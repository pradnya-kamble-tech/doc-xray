"use client"

import { useEffect, useState, useMemo, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
    AnalysisResult,
    ExplainResult,
    StatusEvent,
    getAnalysis,
    createStatusEventSource,
    explainSpan,
    chatWithDocument
} from "@/lib/api"
import { Spinner } from "@/components/ui/spinner"
import { Badge } from "@/components/ui/badge"

export function ViewerClient({ docId }: { docId: string }) {
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [statusEvents, setStatusEvents] = useState<StatusEvent[]>([])
    const [isProcessing, setIsProcessing] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Explain Panel state
    const [selectedSpan, setSelectedSpan] = useState<{ text: string, chunkId: string, type?: string } | null>(null)
    const [explainData, setExplainData] = useState<ExplainResult | null>(null)
    const [isExplaining, setIsExplaining] = useState(false)

    // Visibility filters
    const [filters, setFilters] = useState({
        RISK: true,
        ENTITY: true,
        KEYWORD: true,
        JARGON: true,
        CONCEPT: true
    })

    // Chat Panel state
    const [activeRightTab, setActiveRightTab] = useState<'explain' | 'chat'>('explain')
    const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'ai', text: string, sources?: any[] }[]>([])
    const [chatInput, setChatInput] = useState("")
    const [isChatLoading, setIsChatLoading] = useState(false)
    const chatEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [chatHistory, isChatLoading])


    useEffect(() => {
        // 1. Initial fetch to see if it's already done
        getAnalysis(docId).then(res => {
            setAnalysis(res)
            if (res.status === 'DONE' || res.status === 'FAILED') {
                setIsProcessing(false)
                if (res.status === 'FAILED') setError("Processing failed.")
            } else {
                // 2. Subscribe to SSE if pending
                const es = createStatusEventSource(docId)
                es.onmessage = (e) => {
                    const evt: StatusEvent = JSON.parse(e.data)
                    if (evt.stage === 'heartbeat') return
                    setStatusEvents(prev => [...prev, evt])

                    if (evt.stage === 'Done' || evt.stage === 'Failed') {
                        setIsProcessing(false)
                        es.close()
                        // Reload final data
                        getAnalysis(docId).then(setAnalysis)
                    }
                }
                es.onerror = () => {
                    es.close()
                    setIsProcessing(false)
                }
                return () => es.close()
            }
        }).catch(err => {
            setError(err.message)
            setIsProcessing(false)
        })
    }, [docId])

    // Split text by annotations to inject <mark> tags safely
    const renderChunkWithHighlights = (chunk: AnalysisResult['chunks'][0]) => {
        if (!analysis) return chunk.text

        // Find annotations that belong to this chunk (using strict bounds or chunk_id)
        const activeAnnotations = analysis.annotations.filter(a =>
            a.chunk_id === chunk.id && filters[a.type as keyof typeof filters]
        )

        if (activeAnnotations.length === 0) return chunk.text

        // Ensure they are sorted by char_start to avoid overlap chaos
        activeAnnotations.sort((a, b) => a.char_start - b.char_start)

        let lastIdx = 0
        const elements: React.ReactNode[] = []

        for (let i = 0; i < activeAnnotations.length; i++) {
            const ann = activeAnnotations[i]
            // Because relative text spans inside chunks might vary, simplistic approach:
            // Search for the exact string within the chunk.
            const matchIdx = chunk.text.indexOf(ann.text, lastIdx)

            if (matchIdx !== -1) {
                // text before annotation
                if (matchIdx > lastIdx) {
                    elements.push(<span key={`text-${i}`}>{chunk.text.substring(lastIdx, matchIdx)}</span>)
                }
                // the annotation
                elements.push(
                    <mark
                        key={`mark-${i}`}
                        className={`hl-${ann.type.toLowerCase()}`}
                        onClick={() => handleExplain(ann.text, chunk.id, ann.type)}
                    >
                        {ann.text}
                    </mark>
                )
                lastIdx = matchIdx + ann.text.length
            }
        }
        // remaining text
        if (lastIdx < chunk.text.length) {
            elements.push(<span key={`text-end`}>{chunk.text.substring(lastIdx)}</span>)
        }

        return elements.length > 0 ? elements : chunk.text
    }

    const handleExplain = async (text: string, chunkId: string, type?: string) => {
        setActiveRightTab('explain')
        setSelectedSpan({ text, chunkId, type })
        setIsExplaining(true)
        setExplainData(null)

        try {
            const res = await explainSpan(docId, chunkId, text, type)
            setExplainData(res)
        } catch (err: any) {
            console.error(err)
            // fallback error rendering
        } finally {
            setIsExplaining(false)
        }
    }

    const handleChatSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!chatInput.trim() || isChatLoading) return

        const message = chatInput.trim()
        setChatHistory(prev => [...prev, { role: 'user', text: message }])
        setChatInput("")
        setIsChatLoading(true)

        try {
            const res = await chatWithDocument(docId, message)
            setChatHistory(prev => [...prev, { role: 'ai', text: res.answer, sources: res.sources }])
        } catch (err: any) {
            setChatHistory(prev => [...prev, { role: 'ai', text: "Error: " + err.message }])
        } finally {
            setIsChatLoading(false)
        }
    }

    const latestEvent = statusEvents[statusEvents.length - 1]

    if (error) {
        return <div className="p-8 text-destructive">{error}</div>
    }

    if (isProcessing) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 relative">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
                <Spinner className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-2xl font-bold mb-2">Analyzing Document...</h2>
                <p className="text-muted-foreground mb-8">Passing through multi-stage NLP & ML pipeline</p>

                <div className="w-full max-w-md bg-white/5 rounded-full h-3 overflow-hidden border border-white/10 p-[1px]">
                    <div
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${latestEvent?.percent || 5}%` }}
                    />
                </div>
                <p className="mt-4 text-sm font-medium">{latestEvent?.message || "Initializing..."}</p>
            </div>
        )
    }

    if (!analysis) return null

    // Ensure chunks are properly grouped logically
    return (
        <div className="flex-1 flex h-full">
            {/* LEFT: Document Content */}
            <div className="flex-1 overflow-y-auto p-8 border-r border-white/5 relative">
                <div className="max-w-3xl mx-auto pb-32">

                    <h1 className="text-3xl font-bold mb-8 tracking-tight">Document Viewer</h1>

                    {analysis.summary && (
                        <div className="p-6 mb-8 rounded-xl bg-white/5 border border-white/10 glass shadow-lg">
                            <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-400"><path d="M12 2v20" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
                                AI Summary
                            </h3>
                            <p className="text-muted-foreground leading-relaxed text-sm">
                                {analysis.summary}
                            </p>
                        </div>
                    )}

                    <div className="space-y-6">
                        {analysis.chunks.map(chunk => (
                            <div
                                key={chunk.id}
                                className={`p-5 rounded-lg border leading-relaxed text-sm transition-colors
                  ${chunk.risk_level === 'HIGH_RISK' ? 'border-red-500/20 bg-red-500/5' :
                                        chunk.risk_level === 'MEDIUM_RISK' ? 'border-yellow-500/20 bg-yellow-500/5' :
                                            'border-white/5 bg-white/[0.01] hover:bg-white/[0.03]'}
                `}
                            >
                                {chunk.risk_level !== 'LOW_RISK' && (
                                    <div className="text-xs font-bold mb-2 flex items-center gap-2 uppercase tracking-wide">
                                        {chunk.risk_level === 'HIGH_RISK' ? (
                                            <span className="text-red-500 bg-red-500/10 px-2 py-0.5 rounded-sm">High Risk</span>
                                        ) : (
                                            <span className="text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-sm">Medium Risk</span>
                                        )}
                                        <span className="text-muted-foreground text-[10px]">Source: {chunk.prediction_source}</span>
                                    </div>
                                )}
                                {renderChunkWithHighlights(chunk)}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* RIGHT: Explain Panel & Filters */}
            <div className="w-[400px] flex flex-col bg-black/20 shrink-0">

                {/* Tab Switcher */}
                <div className="flex border-b border-white/5">
                    <button
                        onClick={() => setActiveRightTab('explain')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors ${activeRightTab === 'explain' ? 'bg-white/10 text-white' : 'text-muted-foreground hover:bg-white/5'}`}
                    >
                        Analysis
                    </button>
                    <button
                        onClick={() => setActiveRightTab('chat')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors ${activeRightTab === 'chat' ? 'bg-white/10 text-white' : 'text-muted-foreground hover:bg-white/5'}`}
                    >
                        AI Chat
                    </button>
                </div>

                {activeRightTab === 'explain' && (
                    <>
                        {/* Filters */}
                        <div className="p-6 border-b border-white/5">
                            <h3 className="font-semibold mb-4 tracking-tight">Toggle Highlights</h3>
                            <div className="flex flex-wrap gap-2">
                                {[
                                    { type: 'RISK', c: 'risk', l: `Risks (${(analysis.risk_counts?.HIGH_RISK || 0) + (analysis.risk_counts?.MEDIUM_RISK || 0)})` },
                                    { type: 'ENTITY', c: 'entity', l: `Entities (${Object.keys(analysis.entity_counts).length})` },
                                    { type: 'KEYWORD', c: 'keyword', l: 'Keywords' },
                                    { type: 'JARGON', c: 'jargon', l: 'Jargon' },
                                    { type: 'CONCEPT', c: 'concept', l: 'Concepts' },
                                ].map(f => (
                                    <button
                                        key={f.type}
                                        onClick={() => setFilters(p => ({ ...p, [f.type]: !p[f.type as keyof typeof p] }))}
                                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all
                  ${filters[f.type as keyof typeof filters]
                                                ? `bg-[hsl(var(--hl-${f.c}))]/20 text-[hsl(var(--hl-${f.c}))] border-[hsl(var(--hl-${f.c}))]/30`
                                                : 'bg-white/5 text-muted-foreground border-transparent hover:bg-white/10'
                                            }`}
                                    >
                                        {f.l}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Explain Panel */}
                        <div className="flex-1 overflow-y-auto p-6 relative">
                            <AnimatePresence mode="wait">
                                {!selectedSpan ? (
                                    <motion.div
                                        key="empty"
                                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                        className="h-full flex flex-col items-center justify-center text-center text-muted-foreground/60"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="mb-4 opacity-50"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                                        <p>Click on any highlighted term in the document to get a RAG-powered AI explanation.</p>
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="explainer"
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className="space-y-6"
                                    >
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <Badge variant={selectedSpan.type?.toLowerCase() as any || 'default'}>{selectedSpan.type}</Badge>
                                                <span className="text-xs text-muted-foreground animate-pulse">Explaining...</span>
                                            </div>
                                            <h3 className="text-xl font-bold">"{selectedSpan.text}"</h3>
                                        </div>

                                        {isExplaining ? (
                                            <div className="flex flex-col gap-3">
                                                <div className="h-4 bg-white/10 rounded animate-pulse w-full"></div>
                                                <div className="h-4 bg-white/10 rounded animate-pulse w-[90%]"></div>
                                                <div className="h-4 bg-white/10 rounded animate-pulse w-[95%]"></div>
                                                <div className="h-4 bg-white/10 rounded animate-pulse w-[70%]"></div>
                                            </div>
                                        ) : explainData ? (
                                            <div className="space-y-6 text-sm">
                                                {/* Simplified */}
                                                {explainData.simplified_explanation && (
                                                    <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                                        <strong className="block text-blue-400 mb-1">In plain English:</strong>
                                                        <p className="text-blue-100">{explainData.simplified_explanation}</p>
                                                    </div>
                                                )}

                                                {/* Detailed */}
                                                <div>
                                                    <strong className="block mb-2 text-foreground">Detailed Context:</strong>
                                                    <p className="text-muted-foreground leading-relaxed">{explainData.explanation}</p>
                                                </div>

                                                {/* Grounding Sources */}
                                                {explainData.source_chunks && explainData.source_chunks.length > 0 && (
                                                    <div className="pt-4 border-t border-white/10">
                                                        <strong className="block mb-3 text-xs uppercase tracking-wider text-muted-foreground">Source Citations (RAG)</strong>
                                                        <div className="space-y-3">
                                                            {explainData.source_chunks.slice(0, 2).map(c => (
                                                                <div key={c.chunk_id} className="p-3 bg-white/5 rounded text-xs border border-white/5">
                                                                    <div className="flex justify-between items-center text-[10px] text-muted-foreground/60 mb-1">
                                                                        <span>Page {c.page_num}</span>
                                                                        <span>Sim: {c.similarity_score.toFixed(2)}</span>
                                                                    </div>
                                                                    <p className="line-clamp-3 text-muted-foreground">{c.text}</p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-destructive">Failed to load explanation.</div>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </>
                )}

                {activeRightTab === 'chat' && (
                    <div className="flex-1 flex flex-col overflow-hidden relative">
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {chatHistory.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground/60 p-6">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="mb-4 opacity-50"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
                                    <p>Ask anything about this document. Grounded in the text.</p>
                                </div>
                            ) : (
                                chatHistory.map((item, idx) => (
                                    <div key={idx} className={`flex flex-col ${item.role === 'user' ? 'items-end' : 'items-start'}`}>
                                        <div className={`p-3 rounded-lg text-sm max-w-[85%] ${item.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-white/5 border border-white/10'}`}>
                                            {item.text}
                                        </div>
                                        {item.role === 'ai' && item.sources && item.sources.length > 0 && (
                                            <div className="mt-2 text-xs flex gap-2 flex-wrap max-w-[85%]">
                                                {item.sources.map((src, i) => (
                                                    <span key={i} className="px-2 py-1 bg-white/5 rounded text-muted-foreground border border-white/5">Page {src.page}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                            {isChatLoading && (
                                <div className="flex items-start">
                                    <div className="p-3 py-4 rounded-lg bg-white/5 max-w-[85%] border border-white/10">
                                        <div className="flex space-x-1.5 justify-center items-center h-2">
                                            <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                            <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                            <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce"></div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                        <div className="p-4 border-t border-white/5 bg-black/10 shrink-0">
                            <form onSubmit={handleChatSubmit} className="flex gap-2">
                                <input
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    placeholder="Type your question..."
                                    className="flex-1 bg-white/5 text-sm border-white/10 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-primary/50 transition-all text-white"
                                    disabled={isChatLoading}
                                />
                                <button
                                    type="submit"
                                    disabled={isChatLoading || !chatInput.trim()}
                                    className="px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 font-medium text-sm transition-opacity"
                                >
                                    Send
                                </button>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
