/**
 * Doc-XRay API client — typed wrappers around all backend endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────────────────

export interface Document {
    id: string;
    filename: string;
    original_filename: string;
    file_size: number;
    mime_type: string;
    status: 'PENDING' | 'PROCESSING' | 'DONE' | 'FAILED';
    current_stage?: string;
    error_message?: string;
    page_count: number;
    created_at: string;
    updated_at: string;
}

export interface Annotation {
    id: string;
    chunk_id: string;
    type: 'ENTITY' | 'KEYWORD' | 'JARGON' | 'RISK' | 'CONCEPT';
    label: string;
    text: string;
    char_start: number;
    char_end: number;
    confidence?: number | null;
    page_num: number;
}

export interface Chunk {
    id: string;
    page_num: number;
    text: string;
    char_start: number;
    char_end: number;
    risk_level: 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';
    risk_score: number;
    prediction_source: string;
    tfidf_score: number;
}

export interface AnalysisResult {
    document_id: string;
    status: string;
    page_count: number;
    summary?: string;
    action_items: string[];
    keywords: string[];
    annotations: Annotation[];
    chunks: Chunk[];
    entity_counts: Record<string, number>;
    risk_counts: Record<string, number>;
}

export interface SearchResult {
    chunk_id: string;
    text: string;
    page_num: number;
    similarity_score: number;
    risk_level: string;
    risk_score: number;
}

export interface SearchResponse {
    results: SearchResult[];
    query: string;
    total: number;
}

export interface SourceChunk {
    chunk_id: string;
    text: string;
    page_num: number;
    similarity_score: number;
}

export interface ExplainResult {
    explanation: string;
    simplified_explanation: string;
    risk_level: string;
    confidence?: number | null;
    source_chunks: SourceChunk[];
    source_pages: number[];
    provider: string;
}

export interface StatusEvent {
    stage: string;
    percent: number;
    message: string;
}

export interface ChatSource {
    page: number;
    chunk_id: string;
    similarity: number;
}

export interface ChatResponse {
    answer: string;
    sources: ChatSource[];
}

export interface CompareDifference {
    type: 'ADDED' | 'REMOVED' | 'MODIFIED';
    clause: string;
    description: string;
    sources: { doc: 'A' | 'B'; page: number; chunk_id: string }[];
}

export interface DocumentRisk {
    level: string;
    score: number;
}

export interface CompareResponse {
    similarity_score: number;
    doc_a_risk: DocumentRisk;
    doc_b_risk: DocumentRisk;
    differences: CompareDifference[];
    ai_suggestions: string[];
    error_msg: string | null;
}


// ── Helper ─────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `API error ${res.status}`);
    }
    return res.json();
}

// ── Documents ──────────────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Upload failed: ${res.status}`);
    }
    return res.json();
}

export async function listDocuments(): Promise<{ documents: Document[]; total: number }> {
    return apiFetch('/api/documents/');
}

export async function getDocument(docId: string): Promise<Document> {
    return apiFetch(`/api/documents/${docId}`);
}

export async function deleteDocument(docId: string): Promise<void> {
    await apiFetch(`/api/documents/${docId}`, { method: 'DELETE' });
}

// ── Analysis ────────────────────────────────────────────────────────────

export async function getAnalysis(docId: string): Promise<AnalysisResult> {
    return apiFetch(`/api/analysis/${docId}`);
}

export function createStatusEventSource(docId: string): EventSource {
    return new EventSource(`${API_BASE}/api/analysis/${docId}/status`);
}

// ── Search ──────────────────────────────────────────────────────────────

export async function semanticSearch(
    docId: string,
    query: string,
    topK = 8
): Promise<SearchResponse> {
    return apiFetch('/api/search/', {
        method: 'POST',
        body: JSON.stringify({ doc_id: docId, query, top_k: topK }),
    });
}

// ── Explain ─────────────────────────────────────────────────────────────

export async function explainSpan(
    docId: string,
    chunkId: string,
    spanText: string,
    annotationType?: string
): Promise<ExplainResult> {
    return apiFetch('/api/explain/', {
        method: 'POST',
        body: JSON.stringify({
            doc_id: docId,
            chunk_id: chunkId,
            span_text: spanText,
            annotation_type: annotationType,
        }),
    });
}

// ── Health ──────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string }> {
    return apiFetch('/api/health');
}

// ── Chat ────────────────────────────────────────────────────────────────

export async function chatWithDocument(
    docId: string,
    message: string
): Promise<ChatResponse> {
    return apiFetch(`/api/chat/${docId}`, {
        method: 'POST',
        body: JSON.stringify({ message }),
    });
}

// ── Compare ─────────────────────────────────────────────────────────────

export async function compareDocuments(
    doc1Id: string,
    doc2Id: string
): Promise<CompareResponse> {
    return apiFetch(`/api/compare/${doc1Id}/${doc2Id}`);
}

