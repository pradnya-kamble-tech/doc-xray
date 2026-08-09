"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useDropzone } from "react-dropzone"
import { motion, AnimatePresence } from "framer-motion"
import { uploadDocument } from "@/lib/api"
import { Spinner } from "@/components/ui/spinner"

export default function Home() {
  const router = useRouter()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return
    const file = acceptedFiles[0]

    setIsUploading(true)
    setError(null)

    try {
      const doc = await uploadDocument(file)
      // Redirect to the viewer page which handles processing state
      router.push(`/viewer/${doc.id}`)
    } catch (err: any) {
      setError(err.message || "Failed to upload document")
      setIsUploading(false)
    }
  }, [router])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxFiles: 1,
    disabled: isUploading
  })

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/20 rounded-full blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl w-full text-center z-10"
      >
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          Visual Document <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">Intelligence</span>
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          Upload complex legal, financial, or research documents. Doc-XRay extracts concepts, detects risks, and provides RAG-powered explanations.
        </p>

        <div
          {...getRootProps()}
          className={`
            relative p-12 rounded-2xl border-2 border-dashed transition-all cursor-pointer glass
            ${isDragActive ? 'border-primary bg-primary/5 scale-105' : 'border-white/10 hover:border-white/30 hover:bg-white/5'}
            ${isDragReject ? 'border-destructive bg-destructive/5' : ''}
            ${isUploading ? 'opacity-50 pointer-events-none' : ''}
          `}
        >
          <input {...getInputProps()} />

          <AnimatePresence mode="wait">
            {isUploading ? (
              <motion.div
                key="uploading"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex flex-col items-center gap-4"
              >
                <Spinner className="w-10 h-10 text-primary" />
                <p className="font-medium">Uploading and initializing analysis...</p>
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex flex-col items-center gap-4"
              >
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-muted-foreground"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" x2="12" y1="3" y2="15" /></svg>
                </div>
                <div>
                  <p className="text-xl font-semibold">Drop document here</p>
                  <p className="text-sm text-muted-foreground mt-1">Supports PDF, DOCX (Max 20MB)</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-6 p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-8 flex justify-center w-full"
        >
          <Link href="/compare" className="text-sm font-medium text-white/70 hover:text-white glass px-6 py-3 rounded-full border border-white/10 hover:bg-white/5 hover:border-white/20 transition-all flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 3h5v5" /><path d="M8 3H3v5" /><path d="M12 22v-8" /><path d="M3 11v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8" /></svg>
            Compare Documents
          </Link>
        </motion.div>
      </motion.div>
    </div>
  )
}
