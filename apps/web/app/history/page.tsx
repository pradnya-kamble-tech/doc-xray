"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { format } from "date-fns"
import { listDocuments, deleteDocument, Document } from "@/lib/api"
import { Spinner } from "@/components/ui/spinner"
import { motion, AnimatePresence } from "framer-motion"

export default function HistoryPage() {
    const [docs, setDocs] = useState<Document[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        loadDocs()
    }, [])

    async function loadDocs() {
        try {
            const res = await listDocuments()
            setDocs(res.documents)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setIsLoading(false)
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure you want to delete this document?")) return
        try {
            await deleteDocument(id)
            setDocs(docs => docs.filter(d => d.id !== id))
        } catch (err: any) {
            alert("Failed to delete: " + err.message)
        }
    }

    if (isLoading) {
        return <div className="flex-1 flex items-center justify-center"><Spinner className="w-8 h-8 text-primary" /></div>
    }

    return (
        <div className="max-w-5xl mx-auto w-full p-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Document History</h1>
                    <p className="text-muted-foreground mt-1 text-sm">Previously processed documents and their analyses.</p>
                </div>
                <Link href="/" className="px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 transition-colors">
                    Upload New
                </Link>
            </div>

            {error ? (
                <div className="p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
                    {error}
                </div>
            ) : docs.length === 0 ? (
                <div className="text-center py-24 border border-dashed rounded-xl border-white/10 glass">
                    <p className="text-muted-foreground">No documents found. Upload one to get started.</p>
                </div>
            ) : (
                <div className="grid gap-4">
                    <AnimatePresence>
                        {docs.map((doc, i) => (
                            <motion.div
                                key={doc.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ delay: i * 0.05 }}
                                className="flex items-center justify-between p-5 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] transition-colors"
                            >
                                <div>
                                    <Link href={`/viewer/${doc.id}`} className="font-semibold text-lg hover:underline decoration-white/30 underline-offset-4">
                                        {doc.original_filename}
                                    </Link>
                                    <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                                        <span>{format(new Date(doc.created_at), "MMM d, yyyy h:mm a")}</span>
                                        <span>•</span>
                                        <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                                        <span>•</span>
                                        <span className={`px-2 py-0.5 rounded-full ${doc.status === 'DONE' ? 'bg-green-500/10 text-green-500' :
                                                doc.status === 'FAILED' ? 'bg-red-500/10 text-red-500' :
                                                    'bg-blue-500/10 text-blue-500'
                                            }`}>
                                            {doc.status}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Link href={`/viewer/${doc.id}`} className="px-3 py-1.5 text-sm bg-white/10 hover:bg-white/20 rounded-md transition-colors">
                                        View
                                    </Link>
                                    <button
                                        onClick={() => handleDelete(doc.id)}
                                        className="px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    )
}
