// ─── Types ────────────────────────────────────────────────────────────────────

export interface ReasoningStep {
    type: 'reasoning'
    content: string
    durationSeconds: number
    delay: number
}

export interface PlanStep {
    type: 'plan'
    title: string
    description: string
    tasks: { label: string; status: 'pending' | 'active' | 'complete' }[]
    delay: number
}

export interface ToolCallStep {
    type: 'tool-call'
    toolName: string
    title: string
    input: Record<string, unknown>
    output: Record<string, unknown> | string
    state: 'input-available' | 'output-available' | 'output-error'
    delay: number
    statsUpdate?: Partial<ResearchStats>
}

export interface ContentStep {
    type: 'content'
    content: string
    isStreaming?: boolean
    delay: number
    statsUpdate?: Partial<ResearchStats>
    /** Inline citation markers for this content block */
    citations?: InlineCitationData[]
}

export interface InlineCitationData {
    text: string
    sources: {
        title: string
        url: string
        description: string
    }[]
}

export interface SourcesStep {
    type: 'sources'
    items: { title: string; href: string }[]
    delay: number
}

export interface TaskStep {
    type: 'task'
    title: string
    items: { label: string; file?: string }[]
    delay: number
}

export interface COTSearchResult {
    label: string
    url?: string
}

export interface COTStepData {
    icon: string
    label: string
    status: 'active' | 'complete'
    content: string
    searchResults?: COTSearchResult[]
    image?: {
        src: string
        caption: string
    }
}

export interface ChainOfThoughtStep {
    type: 'chain-of-thought'
    label: string
    steps: COTStepData[]
    delay: number
}

export interface ConfirmationStep {
    type: 'confirmation'
    question: string
    actions: { label: string; value: string }[]
    delay: number
}

export interface PlanUpdateStep {
    type: 'plan-update'
    /** Indices of tasks to mark as complete */
    completeIndices: number[]
    /** Index of the task to mark as active (or -1 for none) */
    activeIndex: number
    delay: number
}

export interface ArtifactStep {
    type: 'artifact'
    title: string
    description: string
    content: string
    delay: number
}

export type ResearchStep =
    | ReasoningStep
    | PlanStep
    | ToolCallStep
    | ContentStep
    | SourcesStep
    | TaskStep
    | ChainOfThoughtStep
    | ConfirmationStep
    | PlanUpdateStep
    | ArtifactStep

export interface ResearchStats {
    tokensUsed: number
    filesReferenced: number
    websitesVisited: number
    docsRead: number
    contextTokens: number
}

export interface ResearchConfig {
    systemPrompt: string
    userPrompt: string
    sources: { type: string; value: string; name?: string }[]
    preferences: {
        enableChat: boolean
        allowBackendResearch: boolean
        template: string
        customInstructions: string
    }
}

// ─── Default System Prompt ────────────────────────────────────────────────────

export const DEFAULT_SYSTEM_PROMPT = `You are Deep Researcher, an advanced AI research agent. Your capabilities include:
- Comprehensive web search and data extraction
- Academic paper analysis and citation management
- Document parsing (PDF, DOCX, TXT)
- Data synthesis and comparative analysis
- Structured report generation with evidence-based citations

Follow the user's research methodology template. Maintain evidence chains and cite all claims. Ask for clarification when the scope is ambiguous.`

// ─── Free image references ────────────────────────────────────────────────────
const IMAGES = {
    aiHealthcare: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=600&h=400&fit=crop',
    medicalAI: 'https://images.unsplash.com/photo-1559757175-5700dde675bc?w=600&h=400&fit=crop',
    drugDiscovery: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=600&h=400&fit=crop',
    hospital: 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=600&h=400&fit=crop',
    dataAnalysis: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&h=400&fit=crop',
}

// ─── Artifact report content ──────────────────────────────────────────────────
export const ARTIFACT_REPORT_CONTENT = `# The Impact of AI on Healthcare: A Comprehensive Analysis

> *This report examines the transformative role of artificial intelligence across healthcare verticals, with a focus on diagnostics, drug discovery, and patient outcomes based on data from 2023-2025.*

---

## Executive Summary

The global AI in healthcare market has reached **$32.4 billion in 2024** and is projected to expand to **$187.95 billion by 2030**, representing a CAGR of 37.5%. This report synthesizes findings from 10+ major publications and databases to provide an evidence-based assessment of AI's impact across three critical domains.

![AI in Healthcare Overview](${IMAGES.aiHealthcare})

---

## 1. AI in Diagnostics

### 1.1 Market Penetration

As of January 2025, the **FDA has authorized 950+ AI/ML-enabled medical devices**, with radiology accounting for approximately **42% of all authorizations** [¹].

| Modality | # FDA-cleared tools | Top Performer | Accuracy |
|----------|-------------------|---------------|----------|
| Chest X-ray | 127 | Qure.ai qXR | 98.2% AUC |
| Mammography | 89 | iCAD ProFound AI | 96.7% sensitivity |
| Retinal Imaging | 64 | IDx-DR | 87.2% sensitivity |
| CT (Stroke) | 52 | Viz.ai LVO | 97.5% sensitivity |
| Pathology (WSI) | 38 | PathAI AISight | 94.3% concordance |

### 1.2 Clinical Evidence

A landmark 2024 meta-analysis across 82 studies found that **AI-assisted radiologists improved diagnostic accuracy by 11.2%** and reduced reading time by 33% compared to unassisted reading [²].

> **"The convergence of large language models, computer vision, and genomic analysis is creating an inflection point in healthcare delivery that was unimaginable five years ago."**
> — Nature Reviews, 2024

![Medical AI Diagnostics](${IMAGES.medicalAI})

### 1.3 Video Resource

For a comprehensive visual overview, see this presentation from MIT on AI in Medical Imaging:

[![AI in Medical Imaging - MIT Lecture](https://img.youtube.com/vi/2HMPRXstSvQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=2HMPRXstSvQ)

---

## 2. AI in Drug Discovery

### 2.1 Timeline Compression

AI-driven drug discovery has demonstrated the potential to reduce the **average $2.6 billion cost** and **12-year timeline** of bringing a new drug to market [³].

![Drug Discovery Pipeline](${IMAGES.drugDiscovery})

### 2.2 Breakthrough Examples

**Insilico Medicine — ISM001-055**
- First AI-discovered drug to complete Phase IIa trials (idiopathic pulmonary fibrosis)
- Preclinical-to-Phase I timeline: **18 months** (vs industry average of 4.5 years)
- Phase IIa results showed statistically significant improvements (p<0.01) [⁴]

**Recursion Pharmaceuticals — REC-994**
- AI-repurposed compound for cerebral cavernous malformation
- Identified through proprietary dataset of 36 petabytes
- Currently in Phase II/III trials

> **Key Insight:** AI-discovered drugs enter Phase II **60% faster** than traditional candidates, with estimated savings of **$300M–$500M** per successful candidate [³].

---

## 3. Impact on Patient Outcomes

### 3.1 Evidence from Randomized Controlled Trials

A JAMA meta-analysis (2024) covering **45 RCTs** with **1.2 million patients** found [⁵]:

| Metric | AI-Assisted | Traditional | Improvement |
|--------|------------|-------------|-------------|
| Time to diagnosis | 2.1 hours | 4.8 hours | **56% faster** |
| Diagnostic accuracy | 94.7% | 87.2% | **+7.5 pp** |
| 30-day readmission | 11.3% | 14.0% | **19% reduction** |
| Length of stay | 4.2 days | 5.1 days | **17.6% shorter** |
| ICU Mortality | 8.1% | 9.4% | **13.8% reduction** |

![Hospital Data Analytics](${IMAGES.hospital})

### 3.2 Disparities & Bias

> ⚠️ **Critical caveat:** A BMJ analysis found that **3 of 7 widely-deployed clinical AI tools exhibited performance gaps of 8–12%** across racial/ethnic groups, primarily due to training data imbalances [⁶].

---

## 4. Ethical & Regulatory Landscape

The **WHO** has established six guiding principles for AI in health:

1. **Protecting human autonomy** — AI augments, not replaces, clinical judgment
2. **Promoting transparency** — Explainability requirements
3. **Ensuring inclusivity** — Mandatory diverse datasets
4. **Fostering responsibility** — Clear liability frameworks
5. **Promoting sustainability** — Environmental impact awareness
6. **Ensuring data privacy** — GDPR, HIPAA compliance [⁷]

---

## 5. Key Takeaways & Recommendations

### For Healthcare Systems
- Prioritize AI adoption in **radiology** and **sepsis prediction** — strongest evidence base and ROI

### For Investors
- Focus on companies with **FDA-cleared products AND strong clinical validation data**

### For Policymakers
- Accelerate frameworks for **continuous learning AI systems** while mandating algorithmic fairness audits

---

## References

[¹] FDA — AI/ML Authorized Medical Devices Database, 2025. https://fda.gov/ai-ml-devices-2025

[²] Nature Reviews — AI in Medicine: Current Trends & Future, 2024. https://nature.com/articles/ai-medicine-2024

[³] The Lancet — AI in Drug Discovery, 2024. https://thelancet.com/ai-drug-discovery

[⁴] Insilico Medicine — ISM001-055 Phase IIa Results, 2024. https://insilico.com/ism001-055-results

[⁵] JAMA — AI-Assisted Diagnosis & Patient Outcomes Meta-Analysis, 2024. https://jamanetwork.com/ai-outcomes-review

[⁶] BMJ — Algorithmic Bias in Clinical AI Tools, 2024. https://bmj.com/algorithmic-bias-2024

[⁷] WHO — Ethics & Governance of AI for Health, 2024. https://who.int/ai-health-guidelines

[⁸] McKinsey & Co. — AI in Healthcare Market Size, 2025. https://mckinsey.com/ai-healthcare-2025

---

*Generated by Deep Researcher • ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}*
`

// ─── Simulated Research Steps ─────────────────────────────────────────────────

export const SIMULATED_RESEARCH_STEPS: ResearchStep[] = [
    // ── Phase 1: Initial Reasoning ──────────────────────────────────────────────
    {
        type: 'reasoning',
        content: `Let me analyze the research request carefully. The user wants a comprehensive analysis of the impact of AI on the healthcare industry, focusing on diagnostics, drug discovery, and patient outcomes. I need to:

1. First understand the current landscape of AI in healthcare
2. Identify key players and technologies
3. Gather recent data (2023-2025) on clinical outcomes
4. Compare traditional vs AI-assisted approaches
5. Look at regulatory frameworks (FDA, EMA)

I should start by searching for recent publications and market reports, then cross-reference with clinical trial data. The user mentioned specific interest in diagnostics — I'll prioritize that but cover all three areas.

Let me also consider the ethical implications and bias concerns that are frequently discussed in recent literature.`,
        durationSeconds: 8,
        delay: 1500,
    },

    // ── Phase 2: Plan of Action (single, will be updated) ───────────────────────
    {
        type: 'plan',
        title: 'Research Plan: AI Impact on Healthcare',
        description: 'A structured approach to analyze AI\'s transformative role across healthcare verticals.',
        tasks: [
            { label: 'Search for recent AI healthcare market reports (2023–2025)', status: 'active' },
            { label: 'Analyze FDA-approved AI medical devices and diagnostics', status: 'pending' },
            { label: 'Review clinical trial data for AI-assisted drug discovery', status: 'pending' },
            { label: 'Compare patient outcomes: AI-assisted vs traditional care', status: 'pending' },
            { label: 'Investigate ethical concerns and regulatory frameworks', status: 'pending' },
            { label: 'Synthesize findings into structured report', status: 'pending' },
        ],
        delay: 800,
    },

    // ── Phase 3: Web search ─────────────────────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'web_search',
        title: 'Searching the web',
        input: {
            query: 'AI healthcare market size growth 2024 2025 report',
            max_results: 10,
            include_domains: ['nature.com', 'thelancet.com', 'mckinsey.com', 'who.int'],
        },
        output: {
            results: [
                { title: 'AI in Healthcare Market Size Report 2025 — McKinsey & Company', url: 'https://mckinsey.com/ai-healthcare-2025' },
                { title: 'Artificial intelligence in medicine: current trends — Nature Reviews', url: 'https://nature.com/articles/ai-medicine-2024' },
                { title: 'FDA Authorized AI/ML Medical Devices — FDA.gov', url: 'https://fda.gov/ai-ml-devices-2025' },
                { title: 'WHO Guidelines on AI for Health — WHO', url: 'https://who.int/ai-health-guidelines' },
                { title: 'The Promise and Peril of AI in Drug Discovery — The Lancet', url: 'https://thelancet.com/ai-drug-discovery' },
            ],
            total_found: 1247,
        },
        state: 'output-available',
        delay: 1200,
        statsUpdate: { websitesVisited: 5, tokensUsed: 2340, contextTokens: 8500 },
    },

    // ── Phase 4: Chain of Thought with search results ───────────────────────────
    {
        type: 'chain-of-thought',
        label: 'Analyzing search results and extracting key data',
        steps: [
            {
                icon: 'search',
                label: 'Processing McKinsey market report',
                status: 'complete',
                content: 'Global AI healthcare market: $32.4B (2024) → $187.95B (2030). CAGR 37.5%.',
                searchResults: [
                    { label: 'mckinsey.com', url: 'https://mckinsey.com/ai-healthcare-2025' },
                    { label: 'nature.com', url: 'https://nature.com/articles/ai-medicine-2024' },
                ],
            },
            {
                icon: 'image',
                label: 'Analyzing FDA device authorization trends',
                status: 'complete',
                content: '950+ AI/ML-enabled devices authorized. Radiology: 42% of all authorizations. 40% increase from 2023.',
                image: {
                    src: IMAGES.dataAnalysis,
                    caption: 'FDA AI/ML device authorization growth trend visualization',
                },
            },
            {
                icon: 'search',
                label: 'Cross-referencing Lancet drug discovery data',
                status: 'complete',
                content: 'AI-discovered drugs enter Phase II 60% faster. Estimated cost savings: $300M–$500M per successful candidate.',
                searchResults: [
                    { label: 'thelancet.com', url: 'https://thelancet.com/ai-drug-discovery' },
                    { label: 'fda.gov', url: 'https://fda.gov/ai-ml-devices-2025' },
                    { label: 'who.int', url: 'https://who.int/ai-health-guidelines' },
                ],
            },
        ],
        delay: 1200,
    },

    // ── Phase 5: Update plan (task 1 complete, task 2 active) ───────────────────
    {
        type: 'plan-update',
        completeIndices: [0],
        activeIndex: 1,
        delay: 400,
    },

    // ── Phase 6: First content generation with inline citations ─────────────────
    {
        type: 'content',
        content: `## Market Overview

The global AI in healthcare market has experienced unprecedented growth, reaching an estimated **$32.4 billion in 2024** and projected to expand to **$187.95 billion by 2030**, representing a compound annual growth rate (CAGR) of 37.5%.

Key growth drivers include:
- **Diagnostic imaging AI** — accounting for 42% of all FDA-authorized AI/ML medical devices
- **Clinical decision support systems** — adopted by 67% of US hospital systems
- **Drug discovery acceleration** — reducing preclinical timelines by an average of 2.5 years

> "The convergence of large language models, computer vision, and genomic analysis is creating an inflection point in healthcare delivery that was unimaginable five years ago." — Nature Reviews, 2024`,
        delay: 1500,
        statsUpdate: { tokensUsed: 4120, contextTokens: 12800 },
        citations: [
            {
                text: '$32.4 billion in 2024',
                sources: [{
                    title: 'AI in Healthcare Market Size Report 2025',
                    url: 'https://mckinsey.com/ai-healthcare-2025',
                    description: 'McKinsey projects the global AI in healthcare market will reach $187.95B by 2030.',
                }],
            },
            {
                text: 'Nature Reviews, 2024',
                sources: [{
                    title: 'Artificial intelligence in medicine: current trends',
                    url: 'https://nature.com/articles/ai-medicine-2024',
                    description: 'Comprehensive review of AI applications across 14 medical imaging modalities.',
                }],
            },
        ],
    },

    // ── Phase 7: Reading uploaded document ──────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'read_document',
        title: 'Reading uploaded document',
        input: {
            file_path: 'healthcare-ai-companies-watchlist.pdf',
            extract_mode: 'structured',
            max_pages: 15,
        },
        output: {
            pages_read: 12,
            extracted_entities: [
                { name: 'PathAI', sector: 'Pathology', key_product: 'AISight platform' },
                { name: 'Tempus', sector: 'Precision Medicine', key_product: 'Genomic sequencing + ML' },
                { name: 'Insilico Medicine', sector: 'Drug Discovery', key_product: 'Chemistry42, PandaOmics' },
                { name: 'Viz.ai', sector: 'Stroke Detection', key_product: 'LVO stroke detection' },
            ],
        },
        state: 'output-available',
        delay: 1800,
        statsUpdate: { docsRead: 1, filesReferenced: 1, tokensUsed: 6530, contextTokens: 18200 },
    },

    // ── Phase 8: Update plan (task 2 complete, task 3 active) ───────────────────
    {
        type: 'plan-update',
        completeIndices: [0, 1],
        activeIndex: 2,
        delay: 400,
    },

    // ── Phase 9: Diagnostics deep-dive content with citations ───────────────────
    {
        type: 'content',
        content: `## 1. AI in Diagnostics

### Imaging & Radiology

AI-powered diagnostic tools have seen the most rapid clinical adoption. As of January 2025, the **FDA has authorized 950+ AI/ML-enabled medical devices**, with radiology accounting for approximately **42% of all authorizations**.

| Modality | # FDA-cleared tools | Top Performer | Accuracy |
|----------|-------------------|---------------|----------|
| Chest X-ray | 127 | Qure.ai qXR | 98.2% AUC |
| Mammography | 89 | iCAD ProFound AI | 96.7% sensitivity |
| Retinal Imaging | 64 | IDx-DR | 87.2% sensitivity |
| CT (Stroke) | 52 | Viz.ai LVO | 97.5% sensitivity |
| Pathology (WSI) | 38 | PathAI AISight | 94.3% concordance |

### Key Finding
A landmark 2024 meta-analysis across 82 studies found that **AI-assisted radiologists improved diagnostic accuracy by 11.2%** and reduced reading time by 33% compared to unassisted reading.`,
        delay: 2200,
        statsUpdate: { tokensUsed: 9200, contextTokens: 24100 },
        citations: [
            {
                text: 'FDA has authorized 950+ AI/ML-enabled medical devices',
                sources: [{
                    title: 'FDA AI/ML Medical Devices Database',
                    url: 'https://fda.gov/ai-ml-devices-2025',
                    description: '950+ AI/ML-enabled devices authorized, 40% increase from 2023.',
                }],
            },
            {
                text: 'improved diagnostic accuracy by 11.2%',
                sources: [{
                    title: 'Nature Reviews — AI in Medicine 2024',
                    url: 'https://nature.com/articles/ai-medicine-2024',
                    description: 'Meta-analysis of 82 studies on AI-assisted radiology performance.',
                }],
            },
        ],
    },

    // ── Phase 10: Confirmation — ask user ───────────────────────────────────────
    {
        type: 'confirmation',
        question: 'I\'ve covered Diagnostics in detail. Should I proceed with an equally detailed analysis of Drug Discovery and Patient Outcomes, or would you prefer a more concise summary?',
        actions: [
            { label: 'Detailed analysis', value: 'detailed' },
            { label: 'Concise summary', value: 'concise' },
        ],
        delay: 800,
    },

    // ── Phase 11: Reasoning after confirmation ──────────────────────────────────
    {
        type: 'reasoning',
        content: `The user approved proceeding with detailed analysis. Let me now tackle Drug Discovery. I need RCT data and company-specific pipeline information.

Key targets:
- Insilico Medicine's ISM001-055 (first AI-discovered drug in Phase IIa)
- Recursion Pharmaceuticals' REC-994
- Timeline compression metrics from The Lancet

Then I'll move to Patient Outcomes with JAMA meta-analysis data.`,
        durationSeconds: 5,
        delay: 800,
    },

    // ── Phase 12: Update plan (task 3 active) ───────────────────────────────────
    {
        type: 'plan-update',
        completeIndices: [0, 1, 2],
        activeIndex: 3,
        delay: 300,
    },

    // ── Phase 13: Tool call — data analysis ─────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'analyze_data',
        title: 'Analyzing clinical trial data',
        input: {
            dataset: 'clinicaltrials.gov',
            query: 'AI artificial intelligence healthcare RCT 2023-2025',
            filters: { phase: ['Phase III', 'Phase IV'], status: 'completed' },
        },
        output: {
            trials_found: 342,
            by_category: {
                diagnostics: 156,
                drug_discovery: 89,
                clinical_decision_support: 54,
                surgical_assistance: 28,
                patient_monitoring: 15,
            },
        },
        state: 'output-available',
        delay: 1500,
        statsUpdate: { websitesVisited: 6, tokensUsed: 11400, contextTokens: 29500 },
    },

    // ── Phase 14: Chain of thought — drug discovery synthesis ──────────────────
    {
        type: 'chain-of-thought',
        label: 'Synthesizing drug discovery findings',
        steps: [
            {
                icon: 'search',
                label: 'Cross-referencing clinical trial data with company pipelines',
                status: 'complete',
                content: 'Matched 14 AI-discovered drug candidates currently in Phase II+ trials across oncology, fibrosis, and neurodegenerative diseases.',
                searchResults: [
                    { label: 'clinicaltrials.gov' },
                    { label: 'insilico.com' },
                    { label: 'recursion.com' },
                ],
            },
            {
                icon: 'search',
                label: 'Calculating timeline compression metrics',
                status: 'complete',
                content: 'Average preclinical-to-Phase I: AI = 1.8 years vs traditional = 4.5 years. 60% reduction. Sample: 23 matched drug pairs.',
            },
            {
                icon: 'image',
                label: 'Analyzing drug discovery pipeline visualization',
                status: 'complete',
                content: 'Estimated cost savings per successful drug candidate: $300M–$500M when AI is used in target identification and lead optimization.',
                image: {
                    src: IMAGES.drugDiscovery,
                    caption: 'AI-accelerated drug discovery pipeline comparison',
                },
            },
        ],
        delay: 1200,
    },

    // ── Phase 15: Drug discovery content ────────────────────────────────────────
    {
        type: 'content',
        content: `## 2. AI in Drug Discovery

AI-driven drug discovery represents perhaps the most commercially significant application, with the potential to reduce the **average $2.6 billion cost** and **12-year timeline** of bringing a new drug to market.

### Breakthrough Examples

**Insilico Medicine — ISM001-055**
- First AI-discovered drug to complete Phase IIa trials (idiopathic pulmonary fibrosis)
- Target identified by PandaOmics, molecule designed by Chemistry42
- Preclinical-to-Phase I timeline: **18 months** (vs industry average of 4.5 years)
- Phase IIa results showed statistically significant improvements (p<0.01)

**Recursion Pharmaceuticals — REC-994**
- AI-repurposed compound for cerebral cavernous malformation
- Identified through 36 petabytes of biological data
- Currently in Phase II/III trials

> **Key Insight:** AI-discovered drugs enter Phase II **60% faster** than traditional candidates, with estimated savings of **$300M–$500M** per successful candidate.`,
        delay: 2500,
        statsUpdate: { tokensUsed: 15800, filesReferenced: 2, contextTokens: 35200 },
        citations: [
            {
                text: 'average $2.6 billion cost',
                sources: [{
                    title: 'The Lancet — AI in Drug Discovery',
                    url: 'https://thelancet.com/ai-drug-discovery',
                    description: 'AI-discovered drugs have entered Phase II trials 60% faster than traditional candidates.',
                }],
            },
        ],
    },

    // ── Phase 16: Update plan ───────────────────────────────────────────────────
    {
        type: 'plan-update',
        completeIndices: [0, 1, 2, 3],
        activeIndex: 4,
        delay: 300,
    },

    // ── Phase 17: Web search for outcomes ───────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'web_search',
        title: 'Searching for patient outcomes data',
        input: {
            query: 'AI healthcare patient outcomes RCT meta-analysis 2024',
            max_results: 8,
        },
        output: {
            results: [
                { title: 'AI-Assisted Diagnosis and Patient Outcomes — JAMA', url: 'https://jamanetwork.com/ai-outcomes-review' },
                { title: 'Algorithmic Bias in Clinical AI Tools — BMJ', url: 'https://bmj.com/algorithmic-bias-2024' },
                { title: 'Impact of AI on Hospital Readmission Rates — Health Affairs', url: 'https://healthaffairs.org/ai-readmissions' },
            ],
        },
        state: 'output-available',
        delay: 1100,
        statsUpdate: { websitesVisited: 9, tokensUsed: 18200, contextTokens: 41000 },
    },

    // ── Phase 18: Task — analyzing outcomes ─────────────────────────────────────
    {
        type: 'task',
        title: 'Processing patient outcomes literature',
        items: [
            { label: 'Extracting RCT data from JAMA systematic review', file: 'jama-ai-outcomes-review.pdf' },
            { label: 'Analyzing bias metrics from BMJ study', file: 'bmj-algorithmic-bias.html' },
            { label: 'Compiling readmission rate data from Health Affairs' },
            { label: 'Cross-referencing with CMS quality measure benchmarks' },
        ],
        delay: 800,
    },

    // ── Phase 19: Patient outcomes content ──────────────────────────────────────
    {
        type: 'content',
        content: `## 3. Impact on Patient Outcomes

### Evidence from Randomized Controlled Trials

A comprehensive JAMA meta-analysis (2024) covering **45 RCTs** with **1.2 million patients** found:

| Metric | AI-Assisted | Traditional | Improvement |
|--------|------------|-------------|-------------|
| Time to diagnosis | 2.1 hours | 4.8 hours | **56% faster** |
| Diagnostic accuracy | 94.7% | 87.2% | **+7.5 pp** |
| 30-day readmission | 11.3% | 14.0% | **19% reduction** |
| Length of stay | 4.2 days | 5.1 days | **17.6% shorter** |
| ICU Mortality | 8.1% | 9.4% | **13.8% reduction** |

### Disparities & Bias

> ⚠️ **Important caveat:** A BMJ analysis of 7 widely-deployed clinical AI tools found that **3 exhibited performance gaps of 8–12%** across racial/ethnic groups, primarily due to training data imbalances.`,
        delay: 2800,
        statsUpdate: { tokensUsed: 23500, docsRead: 3, contextTokens: 49800 },
        citations: [
            {
                text: '45 RCTs',
                sources: [{
                    title: 'JAMA — AI-Assisted Diagnosis & Patient Outcomes',
                    url: 'https://jamanetwork.com/ai-outcomes-review',
                    description: 'Meta-analysis of 45 RCTs with 1.2 million patients on AI-assisted care outcomes.',
                }],
            },
            {
                text: 'performance gaps of 8–12%',
                sources: [{
                    title: 'BMJ — Algorithmic Bias in Clinical AI Tools',
                    url: 'https://bmj.com/algorithmic-bias-2024',
                    description: 'Performance gaps observed across racial/ethnic groups in 3 of 7 studied AI tools.',
                }],
            },
        ],
    },

    // ── Phase 20: Update plan (task 5 active) ───────────────────────────────────
    {
        type: 'plan-update',
        completeIndices: [0, 1, 2, 3, 4],
        activeIndex: 5,
        delay: 300,
    },

    // ── Phase 21: Chain of thought — final synthesis ───────────────────────────
    {
        type: 'chain-of-thought',
        label: 'Final synthesis & quality checks',
        steps: [
            {
                icon: 'search',
                label: 'Verifying all statistical claims against source data',
                status: 'complete',
                content: 'All 14 statistical claims verified against primary sources. No discrepancies found.',
            },
            {
                icon: 'search',
                label: 'Compiling references in APA7 format',
                status: 'complete',
                content: '8 primary sources, 11 secondary sources compiled. Total: 19 citations.',
                searchResults: [
                    { label: '8 primary sources' },
                    { label: '11 secondary sources' },
                    { label: '19 total citations' },
                ],
            },
            {
                icon: 'search',
                label: 'Generating final structured report artifact',
                status: 'complete',
                content: 'Report includes tables, blockquotes, image references, YouTube resource links, and inline citations.',
            },
        ],
        delay: 1000,
    },

    // ── Phase 22: Final conclusion content ─────────────────────────────────────
    {
        type: 'content',
        content: `## Key Takeaways

1. **Market Momentum is Undeniable** — $32.4B (2024) → $187.95B projected (2030). The 37.5% CAGR far outpaces general healthcare IT growth.

2. **Diagnostics Lead Adoption** — 950+ FDA-cleared AI tools. Meta-analyses show 7.5pp accuracy improvements.

3. **Drug Discovery is Being Revolutionized** — AI-discovered drugs reach Phase II **60% faster**, saving **$300M–$500M** per candidate.

4. **Patient Outcomes are Measurably Better** — 56% faster diagnoses, 19% fewer readmissions, 13.8% lower ICU mortality.

5. **Bias Demands Attention** — 8–12% performance gaps across demographics in some tools.`,
        delay: 2000,
        statsUpdate: { tokensUsed: 29100, filesReferenced: 3, websitesVisited: 10, contextTokens: 58700 },
    },

    // ── Phase 23: Update plan (all complete) ────────────────────────────────────
    {
        type: 'plan-update',
        completeIndices: [0, 1, 2, 3, 4, 5],
        activeIndex: -1,
        delay: 400,
    },

    // ── Phase 24: Final sources ─────────────────────────────────────────────────
    {
        type: 'sources',
        items: [
            { title: 'McKinsey & Co. — AI in Healthcare Market Size, 2025', href: 'https://mckinsey.com/ai-healthcare-2025' },
            { title: 'Nature Reviews — AI in Medicine: Current Trends & Future, 2024', href: 'https://nature.com/articles/ai-medicine-2024' },
            { title: 'FDA — AI/ML Authorized Medical Devices, 2025', href: 'https://fda.gov/ai-ml-devices-2025' },
            { title: 'JAMA — AI-Assisted Diagnosis & Patient Outcomes, 2024', href: 'https://jamanetwork.com/ai-outcomes-review' },
            { title: 'BMJ — Algorithmic Bias in Clinical AI Tools, 2024', href: 'https://bmj.com/algorithmic-bias-2024' },
            { title: 'The Lancet — AI in Drug Discovery, 2024', href: 'https://thelancet.com/ai-drug-discovery' },
            { title: 'Health Affairs — AI Impact on Hospital Readmissions, 2024', href: 'https://healthaffairs.org/ai-readmissions' },
            { title: 'WHO — Ethics & Governance of AI for Health, 2024', href: 'https://who.int/ai-health-guidelines' },
        ],
        delay: 500,
    },

    // ── Phase 25: Artifact ──────────────────────────────────────────────────────
    {
        type: 'artifact',
        title: 'AI Impact on Healthcare — Full Research Report',
        description: 'Comprehensive analysis with tables, citations, visuals, and recommendations',
        content: ARTIFACT_REPORT_CONTENT,
        delay: 800,
    },
]
