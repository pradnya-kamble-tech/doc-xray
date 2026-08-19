"use client"

import { useEffect, useState, useRef, useCallback } from "react"
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

type RightTab = 'summary' | 'entities' | 'keywords' | 'chat' | 'filters'

export function ViewerClient({ docId }: { docId: string }) {
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [statusEvents, setStatusEvents] = useState<StatusEvent[]>([])
    const [isProcessing, setIsProcessing] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Explain Panel state
    const [selectedSpan, setSelectedSpan] = useState<{ text: string, chunkId: string, type?: string } | null>(null)
    const [explainData, setExplainData] = useState<ExplainResult | null>(null)
    const [isExplaining, setIsExplaining] = useState(false)

    // Tab state
    const [activeTab, setActiveTab] = useState<RightTab>('summary')

    // Filters
    const [filters, setFilters] = useState({
        RISK: true, ENTITY: true, KEYWORD: true, JARGON: true, CONCEPT: true
    })

    // Chat state
    const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'ai', text: string, sources?: any[] }[]>([])
    const [chatInput, setChatInput] = useState("")
    const [isChatLoading, setIsChatLoading] = useState(false)
    const chatEndRef = useRef<HTMLDivElement>(null)

    // Jump-to-source flash ref
    const flashTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [chatHistory, isChatLoading])

    useEffect(() => {
        getAnalysis(docId).then(res => {
            setAnalysis(res)
            if (res.status === 'DONE' || res.status === 'FAILED') {
                setIsProcessing(false)
                if (res.status === 'FAILED') setError("Processing failed.")
            } else {
                const es = createStatusEventSource(docId)
                es.onmessage = (e) => {
                    const evt: StatusEvent = JSON.parse(e.data)
                    if (evt.stage === 'heartbeat') return
                    setStatusEvents(prev => [...prev, evt])
                    if (evt.stage === 'Done' || evt.stage === 'Failed') {
                        setIsProcessing(false)
                        es.close()
                        getAnalysis(docId).then(setAnalysis)
                    }
                }
                es.onerror = () => { es.close(); setIsProcessing(false) }
                return () => es.close()
            }
        }).catch(err => { setError(err.message); setIsProcessing(false) })
    }, [docId])

    const renderChunkWithHighlights = (chunk: AnalysisResult['chunks'][0]) => {
        if (!analysis) return chunk.text
        const activeAnnotations = analysis.annotations.filter(a =>
            a.chunk_id === chunk.id && filters[a.type as keyof typeof filters]
        )
        if (activeAnnotations.length === 0) return chunk.text
        activeAnnotations.sort((a, b) => a.char_start - b.char_start)
        let lastIdx = 0
        const elements: React.ReactNode[] = []
        for (let i = 0; i < activeAnnotations.length; i++) {
            const ann = activeAnnotations[i]
            const matchIdx = chunk.text.indexOf(ann.text, lastIdx)
            if (matchIdx !== -1) {
                if (matchIdx > lastIdx) elements.push(<span key={`t-${i}`}>{chunk.text.substring(lastIdx, matchIdx)}</span>)
                elements.push(
                    <mark key={`m-${i}`} className={`hl-${ann.type.toLowerCase()}`}
                        onClick={() => handleExplain(ann.text, chunk.id, ann.type)}>
                        {ann.text}
                    </mark>
                )
                lastIdx = matchIdx + ann.text.length
            }
        }
        if (lastIdx < chunk.text.length) elements.push(<span key="t-end">{chunk.text.substring(lastIdx)}</span>)
        return elements.length > 0 ? elements : chunk.text
    }

    const handleExplain = async (text: string, chunkId: string, type?: string) => {
        setActiveTab('summary')
        setSelectedSpan({ text, chunkId, type })
        setIsExplaining(true)
        setExplainData(null)
        try {
            const res = await explainSpan(docId, chunkId, text, type)
            setExplainData(res)
        } catch (err: any) {
            console.error(err)
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

    const jumpToChunk = useCallback((chunkId: string) => {
        const el = document.querySelector(`[data-chunk-id="${chunkId}"]`) as HTMLElement | null
        if (!el) return
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        el.classList.add('chunk-flash')
        if (flashTimeout.current) clearTimeout(flashTimeout.current)
        flashTimeout.current = setTimeout(() => el.classList.remove('chunk-flash'), 2200)
    }, [])

    // Find chunkId from source page number (best effort)
    const findChunkIdByPage = useCallback((page: number, chunkId?: string): string | null => {
        if (chunkId) return chunkId
        if (!analysis) return null
        const c = analysis.chunks.find(c => c.page_num === page)
        return c?.id ?? null
    }, [analysis])

    // Computed risk score (handle 0-1 vs 0-100 gracefully)
    const rawScore = analysis?.risk_score || 0
    const overallRiskScore = Math.round(rawScore <= 1.01 ? rawScore * 100 : rawScore)
    const riskColor = overallRiskScore <= 30 ? 'text-green-400' : overallRiskScore <= 70 ? 'text-yellow-400' : 'text-red-400'
    const riskBarColor = overallRiskScore <= 30 ? 'from-green-500 to-emerald-400' : overallRiskScore <= 70 ? 'from-yellow-500 to-amber-400' : 'from-red-500 to-rose-400'
    const riskLevelStr = analysis?.risk_level?.toUpperCase() === 'HIGH_RISK' ? '🔴 High Risk' : analysis?.risk_level?.toUpperCase() === 'MEDIUM_RISK' ? '🟡 Medium Risk' : '🟢 Low Risk'
    const riskLabel = riskLevelStr

    // Entity groups
    const entityGroups = analysis
        ? Object.entries(analysis.entity_counts).sort((a, b) => b[1] - a[1])
        : []

    const latestEvent = statusEvents[statusEvents.length - 1]

    if (error) return <div className="p-8 text-destructive">{error}</div>

    if (isProcessing) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 relative">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
                <Spinner className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-2xl font-bold mb-2">Analyzing Document...</h2>
                <p className="text-muted-foreground mb-8">Passing through multi-stage NLP &amp; ML pipeline</p>
                <div className="w-full max-w-md bg-white/5 rounded-full h-3 overflow-hidden border border-white/10 p-[1px]">
                    <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${latestEvent?.percent || 5}%` }} />
                </div>
                <p className="mt-4 text-sm font-medium">{latestEvent?.message || "Initializing..."}</p>
            </div>
        )
    }

    if (!analysis) return null

    const TABS: { id: RightTab; label: string; emoji: string }[] = [
        { id: 'summary', label: 'Summary', emoji: '📊' },
        { id: 'entities', label: 'Entities', emoji: '🔵' },
        { id: 'keywords', label: 'Keywords', emoji: '🟡' },
        { id: 'chat', label: 'AI Chat', emoji: '💬' },
        { id: 'filters', label: 'Filters', emoji: '🎛️' },
    ]

    return (
        <div className="flex-1 flex h-full overflow-hidden">
            {/* LEFT: Document Content */}
            <div className="flex-1 overflow-y-auto p-8 border-r border-white/5 relative">
                <div className="max-w-3xl mx-auto pb-32">
                    <h1 className="text-3xl font-bold mb-8 tracking-tight">Document Viewer</h1>
                    <div className="space-y-4">
                        {analysis.chunks.map(chunk => (
                            <div
                                key={chunk.id}
                                data-chunk-id={chunk.id}
                                className={`p-5 rounded-lg border leading-relaxed text-sm transition-all duration-200
                                    ${chunk.risk_level?.toUpperCase() === 'HIGH_RISK' ? 'border-red-500/25 bg-red-500/5' :
                                        chunk.risk_level?.toUpperCase() === 'MEDIUM_RISK' ? 'border-yellow-500/20 bg-yellow-500/5' :
                                            'border-white/5 bg-white/[0.01] hover:bg-white/[0.03]'}`}
                            >
                                {chunk.risk_level !== 'LOW_RISK' && (
                                    <div className="text-xs font-bold mb-2 flex items-center gap-2 uppercase tracking-wide">
                                        {chunk.risk_level?.toUpperCase() === 'HIGH_RISK'
                                            ? <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded-sm">🔴 High Risk</span>
                                            : <span className="text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded-sm">🟡 Medium Risk</span>}
                                        <span className="text-muted-foreground text-[10px]">
                                            score: {Math.round((chunk.risk_score || 0) <= 1.01 ? (chunk.risk_score || 0) * 100 : (chunk.risk_score || 0))}/100
                                        </span>
                                    </div>
                                )}
                                {renderChunkWithHighlights(chunk)}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* RIGHT: Tabbed Panel */}
            <div className="w-[420px] flex flex-col bg-black/20 shrink-0">
                {/* Tab Bar */}
                <div className="flex border-b border-white/10 shrink-0 overflow-x-auto">
                    {TABS.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`flex-1 py-3 text-xs font-semibold transition-all whitespace-nowrap px-2
                                ${activeTab === tab.id
                                    ? 'bg-white/10 text-white border-b-2 border-primary'
                                    : 'text-muted-foreground hover:bg-white/5'}`}>
                            {tab.emoji} {tab.label}
                        </button>
                    ))}
                </div>

                <AnimatePresence mode="wait">
                    {/* ── SUMMARY TAB ── */}
                    {activeTab === 'summary' && (
                        <motion.div key="summary" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 overflow-y-auto p-5 space-y-4">

                            {/* ── Document Type Card ── */}
                            {analysis.document_type && (
                                <div className="p-4 rounded-xl border" style={{
                                    background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.06) 100%)',
                                    borderColor: 'rgba(139,92,246,0.25)'
                                }}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Document Type</span>
                                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/25">
                                            {Math.round((analysis.document_type_confidence || 0) * 100)}% confidence
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-2xl">{analysis.doc_type_emoji || '📄'}</span>
                                        <span className="text-xl font-bold tracking-tight text-white">{analysis.document_type}</span>
                                    </div>
                                    {analysis.doc_type_explanation && (
                                        <p className="text-xs text-muted-foreground/80 leading-relaxed italic">
                                            {analysis.doc_type_explanation}
                                        </p>
                                    )}
                                </div>
                            )}

                            {/* ── Key Information Card ── */}
                            {analysis.key_information && Object.keys(analysis.key_information).length > 0 && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">🗝️ Key Information</h3>
                                    <div className="grid grid-cols-2 gap-y-3 gap-x-2">
                                        {Object.entries(analysis.key_information).map(([key, value]) => (
                                            <div key={key} className="flex flex-col">
                                                <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-0.5">{key}</span>
                                                <span className="text-sm font-medium text-white truncate" title={value}>{value}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}


                            {/* Overall Risk Score Card */}
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Overall Risk</span>
                                    <span className={`text-xs font-bold ${riskColor}`}>{riskLabel}</span>
                                </div>
                                <div className="flex items-end gap-3">
                                    <span className={`text-4xl font-bold tabular-nums ${riskColor}`}>{overallRiskScore}</span>
                                    <span className="text-muted-foreground text-sm mb-1">/ 100</span>
                                </div>
                                <div className="mt-3 h-2.5 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full bg-gradient-to-r ${riskBarColor} transition-all duration-700`}
                                        style={{ width: `${overallRiskScore}%` }} />
                                </div>
                                <div className="mt-2 flex justify-between text-[10px] text-muted-foreground/50">
                                    <span>Low</span><span>Medium</span><span>High</span>
                                </div>
                                {analysis.risk_reasons && analysis.risk_reasons.length > 0 && (
                                    <div className="mt-3 p-2 bg-black/20 rounded-md text-xs text-muted-foreground">
                                        <p className="font-semibold mb-1 text-white/70">Risk Factors:</p>
                                        <ul className="list-disc pl-4 space-y-1">
                                            {analysis.risk_reasons.map((reason: string, i: number) => (
                                                <li key={i}>{reason}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* ── Action Items Card ── */}
                            {analysis.action_items && analysis.action_items.length > 0 && (
                                <div className="p-4 rounded-xl border bg-emerald-500/5 border-emerald-500/20">
                                    <h3 className="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-3">✅ Action Items</h3>
                                    <ul className="space-y-2">
                                        {analysis.action_items.map((action: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-emerald-100/80 leading-snug">
                                                <span className="shrink-0 text-emerald-400">→</span>
                                                <span className="leading-tight">{action}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Metadata Mini-Cards */}
                            <div className="grid grid-cols-2 gap-2">
                                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1">Pages</div>
                                    <div className="text-lg font-bold">{analysis.page_count}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1">Risk Chunks</div>
                                    <div className="text-lg font-bold text-red-400">{(analysis.risk_counts?.HIGH_RISK || 0) + (analysis.risk_counts?.MEDIUM_RISK || 0)}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1">Entities</div>
                                    <div className="text-lg font-bold text-blue-400">{Object.values(analysis.entity_counts).reduce((a, b) => a + b, 0)}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1">Keywords</div>
                                    <div className="text-lg font-bold text-amber-400">{analysis.keywords.length}</div>
                                </div>
                            </div>

                            {/* AI Summary */}
                            {analysis.summary && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">✨ AI Summary</h3>
                                    <p className="text-sm text-muted-foreground leading-relaxed">{analysis.summary}</p>
                                </div>
                            )}



                            {/* Explain Panel — shows when user clicks a highlight */}
                            {selectedSpan && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Badge variant={selectedSpan.type?.toLowerCase() as any || 'default'}>{selectedSpan.type}</Badge>
                                        <span className="text-xs text-muted-foreground">AI Explanation</span>
                                    </div>
                                    <h3 className="text-base font-bold mb-3">"{selectedSpan.text}"</h3>
                                    {isExplaining ? (
                                        <div className="space-y-2">
                                            {[100, 90, 95, 70].map((w, i) => (
                                                <div key={i} className={`h-3 bg-white/10 rounded animate-pulse`} style={{ width: `${w}%` }} />
                                            ))}
                                        </div>
                                    ) : explainData ? (
                                        <div className="space-y-3 text-sm">
                                            {explainData.simplified_explanation && (
                                                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                                    <strong className="block text-blue-400 text-xs mb-1">Plain English:</strong>
                                                    <p className="text-blue-100">{explainData.simplified_explanation}</p>
                                                </div>
                                            )}
                                            <p className="text-muted-foreground leading-relaxed">{explainData.explanation}</p>
                                            {explainData.source_chunks?.length > 0 && (
                                                <div className="pt-3 border-t border-white/10 space-y-2">
                                                    <strong className="block text-xs uppercase tracking-wider text-muted-foreground">Sources</strong>
                                                    {explainData.source_chunks.slice(0, 2).map(c => (
                                                        <div key={c.chunk_id} className="p-2 bg-white/5 rounded text-xs border border-white/5">
                                                            <div className="flex justify-between text-[10px] text-muted-foreground/60 mb-1">
                                                                <span>Page {c.page_num}</span>
                                                                <span>Sim: {c.similarity_score.toFixed(2)}</span>
                                                            </div>
                                                            <p className="line-clamp-2 text-muted-foreground">{c.text}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-destructive text-sm">Failed to load explanation.</div>
                                    )}
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* ── ENTITIES TAB ── */}
                    {activeTab === 'entities' && (
                        <motion.div key="entities" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 overflow-y-auto p-5 space-y-3">
                            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">🔵 Named Entities</h3>
                            {entityGroups.length === 0
                                ? <p className="text-sm text-muted-foreground/50 text-center mt-8">No entities found.</p>
                                : entityGroups.map(([type, count]) => {
                                    const entities = analysis.annotations.filter(a => a.type === 'ENTITY' && a.label === type)
                                    const unique = [...new Set(entities.map(e => e.text))]
                                    return (
                                        <div key={type} className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">{type}</span>
                                                <span className="text-xs text-muted-foreground bg-white/5 px-2 py-0.5 rounded-full">{count}</span>
                                            </div>
                                            <div className="flex flex-wrap gap-1.5">
                                                {unique.slice(0, 10).map((e, i) => (
                                                    <span key={i} className="text-xs px-2 py-0.5 bg-blue-500/10 text-blue-300 rounded border border-blue-500/20">{e}</span>
                                                ))}
                                                {unique.length > 10 && <span className="text-xs text-muted-foreground/50">+{unique.length - 10} more</span>}
                                            </div>
                                        </div>
                                    )
                                })}
                        </motion.div>
                    )}

                    {/* ── KEYWORDS TAB ── */}
                    {activeTab === 'keywords' && (
                        <motion.div key="keywords" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 overflow-y-auto p-5">
                            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">🟡 Top Keywords</h3>
                            {analysis.keywords.length === 0
                                ? <p className="text-sm text-muted-foreground/50 text-center mt-8">No keywords found.</p>
                                : <div className="flex flex-wrap gap-2">
                                    {analysis.keywords.map((kw, i) => (
                                        <span key={i}
                                            className="px-3 py-1.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 transition-colors cursor-default">
                                            {kw}
                                        </span>
                                    ))}
                                </div>}
                        </motion.div>
                    )}

                    {/* ── AI CHAT TAB ── */}
                    {activeTab === 'chat' && (
                        <motion.div key="chat" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 flex flex-col overflow-hidden">
                            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                                {chatHistory.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground/50 p-6 mt-8">
                                        <div className="text-5xl mb-4">💬</div>
                                        <p className="text-sm font-medium">Ask anything about this document.</p>
                                        <p className="text-xs mt-1 opacity-60">Answers are grounded in the document text.</p>
                                    </div>
                                ) : (
                                    chatHistory.map((item, idx) => (
                                        <div key={idx} className={`flex flex-col ${item.role === 'user' ? 'items-end' : 'items-start'}`}>
                                            <div className={`text-xs font-semibold mb-1 ${item.role === 'user' ? 'text-primary/70' : 'text-muted-foreground/60'}`}>
                                                {item.role === 'user' ? 'You' : '🤖 AI'}
                                            </div>
                                            <div className={`p-3 rounded-xl text-sm max-w-[90%] leading-relaxed
                                                ${item.role === 'user'
                                                    ? 'bg-primary text-primary-foreground rounded-tr-sm'
                                                    : 'bg-white/5 border border-white/10 rounded-tl-sm'}`}>
                                                {item.text}
                                            </div>
                                            {item.role === 'ai' && item.sources && item.sources.length > 0 && (
                                                <div className="mt-1.5 flex gap-1.5 flex-wrap">
                                                    {item.sources.map((src, i) => (
                                                        <button key={i}
                                                            onClick={() => jumpToChunk(findChunkIdByPage(src.page, src.chunk_id) || '')}
                                                            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors">
                                                            📄 Page {src.page}
                                                            <span className="text-blue-300/50 ml-0.5">↗</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                                {isChatLoading && (
                                    <div className="flex items-start">
                                        <div className="p-3 py-4 rounded-xl bg-white/5 border border-white/10 rounded-tl-sm">
                                            <div className="flex space-x-1.5">
                                                <div className="w-2 h-2 bg-white/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                <div className="w-2 h-2 bg-white/40 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                <div className="w-2 h-2 bg-white/40 rounded-full animate-bounce" />
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>
                            <div className="p-3 border-t border-white/5 bg-black/10 shrink-0">
                                <form onSubmit={handleChatSubmit} className="flex gap-2">
                                    <input
                                        type="text"
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        placeholder="Ask anything about this document..."
                                        className="flex-1 bg-white/5 text-sm border border-white/10 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-primary/50 transition-all text-white placeholder:text-muted-foreground/40"
                                        disabled={isChatLoading}
                                    />
                                    <button type="submit"
                                        disabled={isChatLoading || !chatInput.trim()}
                                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-40 font-semibold text-sm transition-all hover:opacity-90 shrink-0">
                                        Send
                                    </button>
                                </form>
                            </div>
                        </motion.div>
                    )}

                    {/* ── FILTERS TAB ── */}
                    {activeTab === 'filters' && (
                        <motion.div key="filters" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 overflow-y-auto p-5">
                            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">🎛️ Toggle Highlights</h3>
                            <div className="space-y-3">
                                {[
                                    { type: 'RISK', c: 'risk', l: '🔴 Risk Phrases', count: (analysis.risk_counts?.HIGH_RISK || 0) + (analysis.risk_counts?.MEDIUM_RISK || 0) },
                                    { type: 'ENTITY', c: 'entity', l: '🔵 Named Entities', count: Object.values(analysis.entity_counts).reduce((a, b) => a + b, 0) },
                                    { type: 'KEYWORD', c: 'keyword', l: '🟡 Keywords', count: analysis.keywords.length },
                                    { type: 'JARGON', c: 'jargon', l: '🟣 Jargon', count: analysis.annotations.filter(a => a.type === 'JARGON').length },
                                    { type: 'CONCEPT', c: 'concept', l: '🟢 Concepts', count: analysis.annotations.filter(a => a.type === 'CONCEPT').length },
                                ].map(f => (
                                    <button key={f.type}
                                        onClick={() => setFilters(p => ({ ...p, [f.type]: !p[f.type as keyof typeof p] }))}
                                        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border text-sm font-medium transition-all
                                            ${filters[f.type as keyof typeof filters]
                                                ? 'bg-white/10 border-white/20 text-white'
                                                : 'bg-white/[0.02] border-white/5 text-muted-foreground hover:bg-white/5'}`}>
                                        <span>{f.l}</span>
                                        <span className="text-xs text-muted-foreground">{f.count}</span>
                                    </button>
                                ))}
                            </div>
                            <p className="mt-6 text-xs text-muted-foreground/40 text-center">Click highlighted text in the document to get an AI explanation.</p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    )
}
