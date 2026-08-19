"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import { listDocuments, compareDocuments, Document, CompareResponse, CompareDifference, DocumentRisk } from "@/lib/api"
import { Spinner } from "@/components/ui/spinner"

export default function ComparePage() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [doc1Id, setDoc1Id] = useState<string>("")
    const [doc2Id, setDoc2Id] = useState<string>("")
    const [isComparing, setIsComparing] = useState(false)
    const [result, setResult] = useState<CompareResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isLoadingDocs, setIsLoadingDocs] = useState(true)

    useEffect(() => {
        async function loadDocs() {
            try {
                const res = await listDocuments()
                // Only allow DONE documents for comparison
                const validDocs = res.documents.filter(d => d.status === "DONE")
                setDocuments(validDocs)

                if (validDocs.length >= 2) {
                    setDoc1Id(validDocs[0].id)
                    setDoc2Id(validDocs[1].id)
                }
            } catch (err) {
                console.error("Failed to load documents", err)
            } finally {
                setIsLoadingDocs(false)
            }
        }
        loadDocs()
    }, [])

    const handleCompare = async () => {
        if (!doc1Id || !doc2Id) return
        if (doc1Id === doc2Id) {
            setError("Please select two different documents to compare.")
            return
        }

        setIsComparing(true)
        setError(null)
        setResult(null)

        try {
            const res = await compareDocuments(doc1Id, doc2Id)
            if (res.error_msg) {
                setError(res.error_msg)
            } else {
                setResult(res)
            }
        } catch (err: any) {
            setError(err.message || "Failed to compare documents.")
        } finally {
            setIsComparing(false)
        }
    }

    const renderRisk = (risk: DocumentRisk, title: string) => {
        const isHigh = risk.level === 'HIGH_RISK';
        const isMedium = risk.level === 'MEDIUM_RISK';
        const scoreFormatted = risk?.score != null ? risk.score.toFixed(2) : '0.00';
        return (
            <div className={`p-4 rounded-xl border ${isHigh ? 'border-red-500/30 bg-red-500/10' : isMedium ? 'border-yellow-500/30 bg-yellow-500/10' : 'border-green-500/30 bg-green-500/10'}`}>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-white/50 mb-1">{title} Risk</h4>
                <div className="flex items-center justify-between">
                    <span className={`font-bold ${isHigh ? 'text-red-400' : isMedium ? 'text-yellow-400' : 'text-green-400'}`}>{risk.level ? risk.level.replace('_', ' ') : 'LOW RISK'}</span>
                    <span className="text-sm font-medium opacity-80">{scoreFormatted}</span>
                </div>
            </div>
        )
    }

    const getDocId = (docLabel: 'A' | 'B') => docLabel === 'A' ? doc1Id : doc2Id;

    const renderDiffSection = (diffs: CompareDifference[], type: string, color: string) => {
        const filtered = diffs.filter(d => d.type === type);
        if (filtered.length === 0) return null;

        return (
            <div className={`glass p-6 rounded-2xl border border-${color}-500/20 bg-${color}-500/5 mb-6`}>
                <h3 className={`text-lg font-bold mb-4 flex items-center gap-2 text-${color}-400`}>
                    {type === 'ADDED' ? <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg> : null}
                    {type === 'REMOVED' ? <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /></svg> : null}
                    {type === 'MODIFIED' ? <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg> : null}
                    {type} CLAUSES
                </h3>
                <div className="flex flex-col gap-4">
                    {filtered.map((clause, i) => (
                        <div key={i} className="bg-black/30 border border-white/5 p-4 rounded-xl">
                            <h4 className="font-semibold text-white/90 mb-2">{clause.clause}</h4>
                            <p className="text-sm text-white/70 leading-relaxed mb-3">{clause.description}</p>
                            {clause.sources && clause.sources.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {clause.sources.map((src, j) => (
                                        <Link key={j} href={`/viewer/${getDocId(src.doc)}?page=${src.page}&chunk=${src.chunk_id}`} target="_blank" className="text-xs flex items-center gap-1 bg-white/5 hover:bg-white/10 px-2.5 py-1.5 rounded text-white/60 hover:text-white/90 transition-colors border border-white/10">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></svg>
                                            Doc {src.doc} (Pg {src.page})
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className="flex-1 flex flex-col p-8 max-w-6xl mx-auto w-full relative overflow-y-auto overflow-x-hidden min-h-screen">
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none fixed" />
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 rounded-full blur-[120px] pointer-events-none fixed" />

            <div className="z-10 mb-8 flex items-center justify-between">
                <div>
                    <Link href="/" className="text-sm text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
                        Back to Upload
                    </Link>
                    <h1 className="text-4xl font-bold tracking-tight">
                        Compare <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">v2</span>
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Semantic difference analysis.
                    </p>
                </div>
            </div>

            {isLoadingDocs ? (
                <div className="flex justify-center py-20 z-10"><Spinner className="w-8 h-8" /></div>
            ) : documents.length < 2 ? (
                <div className="z-10 p-12 text-center glass rounded-2xl border border-white/10">
                    <h2 className="text-xl font-semibold mb-2">Not enough documents</h2>
                    <p className="text-muted-foreground mb-6">You need at least 2 processed documents to run a comparison.</p>
                    <Link href="/" className="px-6 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
                        Upload Document
                    </Link>
                </div>
            ) : (
                <div className="z-10 bg-black/20 glass border border-white/10 rounded-2xl p-6 mb-8 flex flex-col md:flex-row gap-6 items-end">
                    <div className="flex-1 w-full">
                        <label className="block text-sm font-medium text-white/80 mb-2">Document A (Baseline)</label>
                        <select
                            value={doc1Id}
                            onChange={e => setDoc1Id(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary/50 transition-colors"
                        >
                            <option value="" disabled>Select Document A</option>
                            {documents.map(d => (
                                <option key={d.id} value={d.id}>{d.original_filename}</option>
                            ))}
                        </select>
                    </div>

                    <div className="hidden md:flex h-12 w-12 items-center justify-center shrink-0 text-muted-foreground mb-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="-ml-3"><path d="m9 18 6-6-6-6" /></svg>
                    </div>

                    <div className="flex-1 w-full">
                        <label className="block text-sm font-medium text-white/80 mb-2">Document B (Comparison)</label>
                        <select
                            value={doc2Id}
                            onChange={e => setDoc2Id(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary/50 transition-colors"
                        >
                            <option value="" disabled>Select Document B</option>
                            {documents.map(d => (
                                <option key={d.id} value={d.id}>{d.original_filename}</option>
                            ))}
                        </select>
                    </div>

                    <button
                        onClick={handleCompare}
                        disabled={isComparing || !doc1Id || !doc2Id}
                        className="w-full md:w-auto px-8 py-3 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center h-[50px] shrink-0"
                    >
                        {isComparing ? <Spinner className="w-5 h-5 mr-2" /> : null}
                        {isComparing ? "Analyzing..." : "Compare"}
                    </button>
                </div>
            )}

            {error && (
                <div className="z-10 p-4 mb-8 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium text-sm flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" x2="12" y1="8" y2="12" /><line x1="12" x2="12.01" y1="16" y2="16" /></svg>
                    {error}
                </div>
            )}

            <AnimatePresence mode="wait">
                {result && (
                    <motion.div
                        key="results"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="z-10 flex flex-col gap-6"
                    >
                        {/* Top Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-2">
                            <div className="glass p-8 rounded-2xl border border-white/10 flex flex-col justify-center relative overflow-hidden">
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Calculated Semantic Similarity</h3>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-6xl font-bold tracking-tighter ${result.similarity_score > 80 ? 'text-green-400' : result.similarity_score > 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                                        {result.similarity_score}%
                                    </span>
                                </div>
                                <div className="mt-6 w-full h-2 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${result.similarity_score}%` }}
                                        transition={{ duration: 1, delay: 0.2 }}
                                        className={`h-full ${result.similarity_score > 80 ? 'bg-green-500' : result.similarity_score > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                    />
                                </div>
                            </div>

                            <div className="glass p-6 rounded-2xl border border-white/10 flex flex-col justify-center gap-4">
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1">Risk Profile Shift</h3>
                                {renderRisk(result.doc_a_risk, "Document A")}
                                {renderRisk(result.doc_b_risk, "Document B")}
                            </div>
                        </div>

                        {/* Differences */}
                        {result.differences && result.differences.length > 0 ? (
                            <>
                                {renderDiffSection(result.differences, 'MODIFIED', 'blue')}
                                {renderDiffSection(result.differences, 'ADDED', 'green')}
                                {renderDiffSection(result.differences, 'REMOVED', 'red')}
                            </>
                        ) : (
                            <div className="glass p-8 rounded-2xl border border-white/10 text-center">
                                <p className="text-muted-foreground font-medium">No significant differences detected between the selected documents.</p>
                            </div>
                        )}

                        {/* Suggestions */}
                        {result.ai_suggestions && result.ai_suggestions.length > 0 && (
                            <div className="glass p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5 mt-2">
                                <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-purple-400">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /></svg>
                                    AI Recommendations
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {result.ai_suggestions.map((sug, i) => (
                                        <div key={i} className="flex gap-3 text-sm text-white/80 items-start bg-black/40 p-4 rounded-lg">
                                            <div className="text-purple-400 mt-0.5">•</div>
                                            <div>{sug}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
