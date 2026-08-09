"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import { listDocuments, compareDocuments, Document, CompareResponse } from "@/lib/api"
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
                // Filter out non-DONE documents to only show processed ones
                const validDocs = res.documents.filter(d => d.status === "DONE" || d.status === "PENDING")
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
            setResult(res)
        } catch (err: any) {
            setError(err.message || "Failed to compare documents.")
        } finally {
            setIsComparing(false)
        }
    }

    return (
        <div className="flex-1 flex flex-col p-8 max-w-6xl mx-auto w-full relative overflow-y-auto overflow-x-hidden min-h-screen">
            {/* Background gradients */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none fixed" />
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 rounded-full blur-[120px] pointer-events-none fixed" />

            <div className="z-10 mb-8 flex items-center justify-between">
                <div>
                    <Link href="/" className="text-sm text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
                        Back to Upload
                    </Link>
                    <h1 className="text-4xl font-bold tracking-tight">
                        Compare <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">Documents</span>
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Select two processed documents to perform an AI-powered semantic comparison.
                    </p>
                </div>
            </div>

            {isLoadingDocs ? (
                <div className="flex justify-center py-20 z-10"><Spinner className="w-8 h-8" /></div>
            ) : documents.length < 2 ? (
                <div className="z-10 p-12 text-center glass rounded-2xl border border-white/10">
                    <h2 className="text-xl font-semibold mb-2">Not enough documents</h2>
                    <p className="text-muted-foreground mb-6">You need at least 2 uploaded documents to run a comparison.</p>
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
                <div className="z-10 p-4 mb-8 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 font-medium text-sm">
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
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="glass p-6 rounded-2xl border border-white/10 flex flex-col itesm-center justify-center relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-10">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" x2="22" y1="12" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
                                </div>
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Overall Similarity</h3>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-5xl font-bold tracking-tighter ${result.similarity_score > 80 ? 'text-green-400' : result.similarity_score > 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                                        {result.similarity_score}%
                                    </span>
                                </div>
                                <div className="mt-4 w-full h-2 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${result.similarity_score}%` }}
                                        transition={{ duration: 1, delay: 0.2 }}
                                        className={`h-full ${result.similarity_score > 80 ? 'bg-green-500' : result.similarity_score > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                    />
                                </div>
                            </div>

                            <div className="glass p-6 rounded-2xl border border-white/10 flex flex-col justify-center">
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Risk Difference</h3>
                                <p className="text-lg text-white/90 leading-relaxed font-medium">
                                    {result.risk_difference}
                                </p>
                            </div>
                        </div>

                        {/* Changed Clauses */}
                        {result.changed_clauses && result.changed_clauses.length > 0 && (
                            <div className="glass p-6 rounded-2xl border border-white/10">
                                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                                    Changed Clauses
                                </h3>
                                <div className="flex flex-col gap-3">
                                    {result.changed_clauses.map((clause, i) => (
                                        <div key={i} className="bg-black/30 border border-white/5 p-4 rounded-xl">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="font-semibold text-white/90">{clause.clause}</span>
                                                <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-300 font-medium uppercase">{clause.type}</span>
                                            </div>
                                            <p className="text-sm text-white/70 leading-relaxed">{clause.diff}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Other differences */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {result.added_clauses && result.added_clauses.length > 0 && (
                                <div className="glass p-6 rounded-2xl border border-green-500/20 bg-green-500/5">
                                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-green-400">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg>
                                        Added Clauses
                                    </h3>
                                    <ul className="list-disc pl-5 space-y-2 text-white/80">
                                        {result.added_clauses.map((item, i) => <li key={i}>{item}</li>)}
                                    </ul>
                                </div>
                            )}

                            {result.removed_clauses && result.removed_clauses.length > 0 && (
                                <div className="glass p-6 rounded-2xl border border-red-500/20 bg-red-500/5">
                                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-400">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /></svg>
                                        Removed Clauses
                                    </h3>
                                    <ul className="list-disc pl-5 space-y-2 text-white/80">
                                        {result.removed_clauses.map((item, i) => <li key={i}>{item}</li>)}
                                    </ul>
                                </div>
                            )}
                        </div>

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
