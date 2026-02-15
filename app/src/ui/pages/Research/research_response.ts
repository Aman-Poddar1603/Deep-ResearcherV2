// ─── Types ────────────────────────────────────────────────────────────────────

export interface ReasoningStep {
    type: 'reasoning'
    content: string
    durationSeconds: number
    delay: number // ms before this step appears
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

export interface ChainOfThoughtStep {
    type: 'chain-of-thought'
    label: string
    steps: { icon: string; label: string; status: 'active' | 'complete'; content: string }[]
    delay: number
}

export interface ConfirmationStep {
    type: 'confirmation'
    question: string
    autoApproveDelay: number // ms after which the step auto-approves
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

Let me also consider the ethical implications and bias concerns that are frequently discussed in recent literature. This will make the analysis more balanced and thorough.`,
        durationSeconds: 8,
        delay: 1500,
    },

    // ── Phase 2: Plan of Action ─────────────────────────────────────────────────
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
                { title: 'AI in Healthcare Market Size Report 2025 — McKinsey & Company', url: 'https://mckinsey.com/ai-healthcare-2025', snippet: 'The global AI in healthcare market is projected to reach $187.95 billion by 2030...' },
                { title: 'Artificial intelligence in medicine: current trends — Nature Reviews', url: 'https://nature.com/articles/ai-medicine-2024', snippet: 'Deep learning models have achieved radiologist-level performance in 14 medical imaging tasks...' },
                { title: 'FDA Authorized AI/ML Medical Devices — FDA.gov', url: 'https://fda.gov/ai-ml-devices-2025', snippet: '950+ AI/ML-enabled devices now authorized, a 40% increase from 2023...' },
                { title: 'WHO Guidelines on AI for Health — WHO', url: 'https://who.int/ai-health-guidelines', snippet: 'Six guiding principles for AI in health: transparency, accountability, inclusivity...' },
                { title: 'The Promise and Peril of AI in Drug Discovery — The Lancet', url: 'https://thelancet.com/ai-drug-discovery', snippet: 'AI-discovered drugs have entered Phase II trials 60% faster than traditional candidates...' },
            ],
            total_found: 1247,
        },
        state: 'output-available',
        delay: 1200,
        statsUpdate: { websitesVisited: 5, tokensUsed: 2340, contextTokens: 8500 },
    },

    // ── Phase 4: Reading search results ─────────────────────────────────────────
    {
        type: 'task',
        title: 'Analyzing search results',
        items: [
            { label: 'Extracting key data from McKinsey market report', file: 'mckinsey-ai-healthcare-2025.pdf' },
            { label: 'Reading Nature Reviews article on imaging AI', file: 'nature-ai-medicine-review.html' },
            { label: 'Parsing FDA device authorization database', file: 'fda-ml-devices-2025.json' },
            { label: 'Reviewing WHO guidelines for compliance angles' },
            { label: 'Analyzing Lancet drug discovery timeline data' },
        ],
        delay: 600,
    },

    // ── Phase 5: First content generation ───────────────────────────────────────
    {
        type: 'content',
        content: `## Market Overview

The global AI in healthcare market has experienced unprecedented growth, reaching an estimated **$32.4 billion in 2024** and projected to expand to **$187.95 billion by 2030**, representing a compound annual growth rate (CAGR) of 37.5% (McKinsey, 2025).

Key growth drivers include:
- **Diagnostic imaging AI** — accounting for 42% of all FDA-authorized AI/ML medical devices
- **Clinical decision support systems** — adopted by 67% of US hospital systems
- **Drug discovery acceleration** — reducing preclinical timelines by an average of 2.5 years

> "The convergence of large language models, computer vision, and genomic analysis is creating an inflection point in healthcare delivery that was unimaginable five years ago." — Nature Reviews, 2024`,
        delay: 1500,
        statsUpdate: { tokensUsed: 4120, contextTokens: 12800 },
    },

    // ── Phase 6: Second reasoning ───────────────────────────────────────────────
    {
        type: 'reasoning',
        content: `Good, I've established the market context. Now I need to dive deeper into the three specific areas the user highlighted:

1. **Diagnostics** — I should look at the FDA device database for specific AI tools and their clinical validation data. Radiology and pathology are the most mature areas.

2. **Drug Discovery** — The Lancet article mentioned 60% faster Phase II entry. I need to find specific examples like Insilico Medicine's ISM001-055 and Recursion Pharmaceuticals' work.

3. **Patient Outcomes** — This is the hardest to quantify. I'll search for randomized controlled trials comparing AI-assisted vs standard care.

Let me also pull the user's uploaded document to cross-reference any specific companies or technologies they're interested in.`,
        durationSeconds: 6,
        delay: 1000,
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
                { name: 'PathAI', sector: 'Pathology', stage: 'Series D', key_product: 'AISight platform' },
                { name: 'Tempus', sector: 'Precision Medicine', stage: 'Public (TEM)', key_product: 'Genomic sequencing + ML' },
                { name: 'Insilico Medicine', sector: 'Drug Discovery', stage: 'Series D', key_product: 'Chemistry42, PandaOmics' },
                { name: 'Viz.ai', sector: 'Stroke Detection', stage: 'Acquired', key_product: 'LVO stroke detection' },
            ],
            summary: 'Document outlines 12 key AI healthcare companies across diagnostics, drug discovery, and clinical workflow optimization.',
        },
        state: 'output-available',
        delay: 1800,
        statsUpdate: { docsRead: 1, filesReferenced: 1, tokensUsed: 6530, contextTokens: 18200 },
    },

    // ── Phase 8: Sources listing ────────────────────────────────────────────────
    {
        type: 'sources',
        items: [
            { title: 'McKinsey — AI in Healthcare Market 2025', href: 'https://mckinsey.com/ai-healthcare-2025' },
            { title: 'Nature Reviews — AI in Medicine 2024', href: 'https://nature.com/articles/ai-medicine-2024' },
            { title: 'FDA — AI/ML Medical Devices Database', href: 'https://fda.gov/ai-ml-devices-2025' },
            { title: 'WHO — AI for Health Guidelines', href: 'https://who.int/ai-health-guidelines' },
            { title: 'The Lancet — AI in Drug Discovery', href: 'https://thelancet.com/ai-drug-discovery' },
            { title: 'User Upload — Healthcare AI Companies Watchlist', href: '#' },
        ],
        delay: 500,
    },

    // ── Phase 9: Diagnostics deep-dive content ──────────────────────────────────
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
A landmark 2024 meta-analysis across 82 studies found that **AI-assisted radiologists improved diagnostic accuracy by 11.2%** and reduced reading time by 33% compared to unassisted reading (Nature Reviews, 2024).

### Clinical Impact
Viz.ai's stroke detection system, deployed in 1,400+ hospitals, has demonstrated a **median 26-minute reduction in time to treatment**, directly correlating with improved patient outcomes in large vessel occlusion strokes.`,
        delay: 2200,
        statsUpdate: { tokensUsed: 9200, contextTokens: 24100 },
    },

    // ── Phase 10: Tool call — data analysis ─────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'analyze_data',
        title: 'Analyzing clinical trial data',
        input: {
            dataset: 'clinicaltrials.gov',
            query: 'AI artificial intelligence healthcare randomized controlled trial 2023-2025',
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
            key_insight: 'Diagnostic AI trials show 23% higher completion rates vs traditional trials, suggesting stronger protocol adherence and clearer endpoints.',
        },
        state: 'output-available',
        delay: 1500,
        statsUpdate: { websitesVisited: 6, tokensUsed: 11400, contextTokens: 29500 },
    },

    // ── Phase 11: Chain of thought ──────────────────────────────────────────────
    {
        type: 'chain-of-thought',
        label: 'Synthesizing drug discovery findings',
        steps: [
            {
                icon: 'search',
                label: 'Cross-referencing clinical trial data with company pipelines',
                status: 'complete',
                content: 'Matched 14 AI-discovered drug candidates currently in Phase II+ trials across oncology, fibrosis, and neurodegenerative diseases.',
            },
            {
                icon: 'search',
                label: 'Calculating timeline compression metrics',
                status: 'complete',
                content: 'Average preclinical-to-Phase I timeline: AI-assisted = 1.8 years vs traditional = 4.5 years. Reduction: 60%. Sample size: 23 matched drug pairs.',
            },
            {
                icon: 'search',
                label: 'Evaluating cost-effectiveness data',
                status: 'complete',
                content: 'Estimated cost savings per successful drug candidate: $300M–$500M when AI is used in target identification and lead optimization stages.',
            },
        ],
        delay: 1200,
    },

    // ── Phase 12: Drug discovery content ────────────────────────────────────────
    {
        type: 'content',
        content: `## 2. AI in Drug Discovery

AI-driven drug discovery represents perhaps the most commercially significant application of AI in healthcare, with the potential to reduce the **average $2.6 billion cost** and **12-year timeline** of bringing a new drug to market.

### Breakthrough Examples

**Insilico Medicine — ISM001-055**
- First AI-discovered drug to complete Phase IIa trials (idiopathic pulmonary fibrosis)
- Target identified by PandaOmics, molecule designed by Chemistry42
- Preclinical-to-Phase I timeline: **18 months** (vs industry average of 4.5 years)
- Phase IIa results showed statistically significant improvements in lung function (p<0.01)

**Recursion Pharmaceuticals — REC-994**
- AI-repurposed compound for cerebral cavernous malformation
- Identified through Recursion's proprietary biological dataset of 36 petabytes
- Currently in Phase II/III trials

### Timeline Compression

\`\`\`
Traditional Pipeline:    ████████████████████████████████████  ~12 years
                        Target  Lead  Preclin  Ph.I  Ph.II  Ph.III  Approval

AI-Assisted Pipeline:   ██████████████████████               ~5-7 years
                        Target+Lead  Preclin  Ph.I  Ph.II  Ph.III  Approval
                        (AI accel.)  (AI opt.)
\`\`\`

Cross-referencing the user's watchlist document: **Insilico Medicine** and **Recursion** are both included, validating the document's focus on leading AI drug discovery companies.`,
        delay: 2500,
        statsUpdate: { tokensUsed: 15800, filesReferenced: 2, contextTokens: 35200 },
    },

    // ── Phase 13: Confirmation ──────────────────────────────────────────────────
    {
        type: 'confirmation',
        question: 'I\'ve covered Diagnostics and Drug Discovery in depth. Should I proceed with an equally detailed analysis of Patient Outcomes, or would you prefer a more concise summary to keep the report focused?',
        autoApproveDelay: 4000,
        delay: 800,
    },

    // ── Phase 14: Reasoning after confirmation ──────────────────────────────────
    {
        type: 'reasoning',
        content: `The user approved proceeding with the detailed analysis. Let me now tackle Patient Outcomes, which requires a different approach — I need RCT data and meta-analyses rather than market reports.

I should search for systematic reviews that directly compare AI-assisted vs traditional care pathways. Key metrics to look for:
- Mortality rates
- Length of hospital stay
- Readmission rates
- Diagnostic accuracy in real-world settings
- Patient satisfaction scores

I also want to address the disparities issue — several studies have shown AI tools can perform poorly on underrepresented populations if training data is biased.`,
        durationSeconds: 5,
        delay: 1000,
    },

    // ── Phase 15: Web search for outcomes ───────────────────────────────────────
    {
        type: 'tool-call',
        toolName: 'web_search',
        title: 'Searching for patient outcomes data',
        input: {
            query: 'AI healthcare patient outcomes randomized controlled trial meta-analysis 2024',
            max_results: 8,
        },
        output: {
            results: [
                { title: 'AI-Assisted Diagnosis and Patient Outcomes: A Systematic Review — JAMA', url: 'https://jamanetwork.com/ai-outcomes-review', snippet: 'Meta-analysis of 45 RCTs shows 15.3% improvement in time-to-diagnosis...' },
                { title: 'Algorithmic Bias in Clinical AI Tools — BMJ', url: 'https://bmj.com/algorithmic-bias-2024', snippet: 'Performance gaps of 8-12% observed across racial/ethnic groups in 3 of 7 studied tools...' },
                { title: 'Impact of AI on Hospital Readmission Rates — Health Affairs', url: 'https://healthaffairs.org/ai-readmissions', snippet: '19% reduction in 30-day readmission when AI prediction models guide discharge planning...' },
            ],
            total_found: 892,
        },
        state: 'output-available',
        delay: 1100,
        statsUpdate: { websitesVisited: 9, tokensUsed: 18200, contextTokens: 41000 },
    },

    // ── Phase 16: Task — analyzing outcomes ─────────────────────────────────────
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

    // ── Phase 17: Patient outcomes content ──────────────────────────────────────
    {
        type: 'content',
        content: `## 3. Impact on Patient Outcomes

### Evidence from Randomized Controlled Trials

A comprehensive JAMA meta-analysis (2024) covering **45 randomized controlled trials** with a combined **1.2 million patients** found:

| Metric | AI-Assisted | Traditional | Improvement |
|--------|------------|-------------|-------------|
| Time to diagnosis | 2.1 hours | 4.8 hours | **56% faster** |
| Diagnostic accuracy | 94.7% | 87.2% | **+7.5 pp** |
| 30-day readmission | 11.3% | 14.0% | **19% reduction** |
| Length of stay (avg) | 4.2 days | 5.1 days | **17.6% shorter** |
| Mortality (ICU) | 8.1% | 9.4% | **13.8% reduction** |

### Notable Finding: Disparities & Bias

> ⚠️ **Important caveat:** A BMJ analysis of 7 widely-deployed clinical AI tools found that **3 exhibited performance gaps of 8–12%** across racial/ethnic groups, primarily due to training data imbalances. This underscores the critical need for diverse, representative training datasets and ongoing monitoring.

### Real-World Impact Stories

1. **Sepsis prediction (EPIC Sepsis Model):** Deployed across 200+ hospitals, demonstrating a **22% reduction in sepsis mortality** when alerts were acted upon within the recommended window.

2. **AI-powered discharge planning:** Health Affairs reports that hospitals using ML-driven discharge risk models saw a **19% reduction in 30-day readmissions**, saving an estimated $4,200 per avoided readmission.

3. **Stroke detection (Viz.ai):** The EXPEDITE study showed AI-notified stroke teams activated in a median of **6 minutes** vs **21 minutes** for standard paging, translating to significantly better functional outcomes at 90 days.`,
        delay: 2800,
        statsUpdate: { tokensUsed: 23500, docsRead: 3, contextTokens: 49800 },
    },

    // ── Phase 18: Tool call — citation management ──────────────────────────────
    {
        type: 'tool-call',
        toolName: 'compile_citations',
        title: 'Compiling citations and references',
        input: {
            format: 'APA7',
            sources: ['mckinsey-2025', 'nature-reviews-2024', 'fda-devices-2025', 'jama-meta-2024', 'bmj-bias-2024', 'lancet-drug-discovery-2024', 'health-affairs-readmissions'],
            dedup: true,
        },
        output: {
            total_citations: 18,
            primary_sources: 7,
            secondary_sources: 11,
            formatted: 'Successfully compiled 18 APA7 citations across 7 primary and 11 secondary sources.',
        },
        state: 'output-available',
        delay: 900,
        statsUpdate: { tokensUsed: 24800, contextTokens: 52300 },
    },

    // ── Phase 19: Chain of thought — final synthesis ───────────────────────────
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
                label: 'Checking for balanced representation of risks and benefits',
                status: 'complete',
                content: 'Included bias concerns (BMJ), regulatory challenges, and data privacy issues alongside benefits.',
            },
            {
                icon: 'search',
                label: 'Generating executive summary and key recommendations',
                status: 'complete',
                content: 'Compiled 5 key takeaways and 3 actionable recommendations for stakeholders.',
            },
        ],
        delay: 1000,
    },

    // ── Phase 20: Updated plan with completions ─────────────────────────────────
    {
        type: 'plan',
        title: 'Research Plan: AI Impact on Healthcare',
        description: 'All research phases completed. Generating final report.',
        tasks: [
            { label: 'Search for recent AI healthcare market reports (2023–2025)', status: 'complete' },
            { label: 'Analyze FDA-approved AI medical devices and diagnostics', status: 'complete' },
            { label: 'Review clinical trial data for AI-assisted drug discovery', status: 'complete' },
            { label: 'Compare patient outcomes: AI-assisted vs traditional care', status: 'complete' },
            { label: 'Investigate ethical concerns and regulatory frameworks', status: 'complete' },
            { label: 'Synthesize findings into structured report', status: 'active' },
        ],
        delay: 600,
    },

    // ── Phase 21: Regulatory & ethics content ───────────────────────────────────
    {
        type: 'content',
        content: `## 4. Regulatory Landscape & Ethical Considerations

### FDA Regulatory Framework

The FDA has evolved its approach to AI/ML-based Software as a Medical Device (SaMD):

- **Predetermined Change Control Plan (PCCP):** Introduced in 2024, allowing manufacturers to pre-specify modifications to AI algorithms without requiring new submissions for each update.
- **Total Authorized Devices:** 950+ as of Jan 2025 (up from 692 in Jan 2024)
- **Real-World Performance (RWP) monitoring** now required for all Class III AI devices

### WHO Guiding Principles

The WHO's 2024 updated guidelines establish six principles for ethical AI in health:
1. **Protecting human autonomy** — AI should augment, not replace, clinical judgment
2. **Promoting transparency** — Explainability requirements for clinical AI
3. **Ensuring inclusivity** — Mandatory diverse dataset requirements
4. **Fostering responsibility** — Clear liability frameworks
5. **Promoting sustainability** — Environmental impact of large-scale AI training
6. **Ensuring data privacy** — Compliance with GDPR, HIPAA, and emerging frameworks

### Key Risk: Algorithmic Bias

The BMJ's comprehensive analysis highlights that algorithmic bias remains the most pressing ethical challenge, with **systematic underperformance on minority populations** observed in dermatology, pulmonary function, and cardiac risk prediction tools.`,
        delay: 2200,
        statsUpdate: { tokensUsed: 29100, filesReferenced: 3, websitesVisited: 10, contextTokens: 58700 },
    },

    // ── Phase 22: Final comprehensive conclusion ───────────────────────────────
    {
        type: 'content',
        content: `## Executive Summary & Key Takeaways

### The Bottom Line

AI is fundamentally transforming healthcare across **diagnostics**, **drug discovery**, and **patient outcomes**, with measurable, evidence-based improvements at every stage of the care continuum.

### Five Key Takeaways

1. **Market Momentum is Undeniable** — $32.4B market (2024) → $187.95B projected (2030). The 37.5% CAGR far outpaces general healthcare IT growth.

2. **Diagnostics Lead Adoption** — With 950+ FDA-cleared AI tools, diagnostic AI is the most mature category. Meta-analyses show 7.5 percentage point accuracy improvements.

3. **Drug Discovery is Being Revolutionized** — AI-discovered drugs reach Phase II **60% faster**, with estimated savings of $300M–$500M per successful candidate.

4. **Patient Outcomes are Measurably Better** — RCTs demonstrate 56% faster diagnoses, 19% fewer readmissions, and 13.8% lower ICU mortality with AI assistance.

5. **Bias and Ethics Demand Attention** — Performance gaps of 8–12% across demographics represent a critical challenge that must be addressed through regulation and diverse training data.

### Recommendations

- **For Healthcare Systems:** Prioritize AI adoption in radiology and sepsis prediction — these show the strongest evidence base and ROI.
- **For Investors:** Focus on companies with FDA-cleared products AND strong clinical validation data, particularly in the diagnostic AI space.
- **For Policymakers:** Accelerate frameworks for continuous learning AI systems while mandating algorithmic fairness audits.

---

*Research completed. 10 websites analyzed, 3 documents processed, 18 citations compiled. Total context: ~58,700 tokens.*`,
        delay: 3000,
        statsUpdate: { tokensUsed: 34200, contextTokens: 64500 },
    },

    // ── Final sources ──────────────────────────────────────────────────────────
    {
        type: 'sources',
        items: [
            { title: 'McKinsey & Co. — AI in Healthcare Market Size, 2025', href: 'https://mckinsey.com/ai-healthcare-2025' },
            { title: 'Nature Reviews — AI in Medicine: Current Trends & Future, 2024', href: 'https://nature.com/articles/ai-medicine-2024' },
            { title: 'FDA — AI/ML Authorized Medical Devices, 2025', href: 'https://fda.gov/ai-ml-devices-2025' },
            { title: 'JAMA — AI-Assisted Diagnosis & Patient Outcomes Meta-Analysis, 2024', href: 'https://jamanetwork.com/ai-outcomes-review' },
            { title: 'BMJ — Algorithmic Bias in Clinical AI Tools, 2024', href: 'https://bmj.com/algorithmic-bias-2024' },
            { title: 'The Lancet — AI in Drug Discovery, 2024', href: 'https://thelancet.com/ai-drug-discovery' },
            { title: 'Health Affairs — AI Impact on Hospital Readmissions, 2024', href: 'https://healthaffairs.org/ai-readmissions' },
            { title: 'WHO — Ethics & Governance of AI for Health, 2024', href: 'https://who.int/ai-health-guidelines' },
        ],
        delay: 500,
    },
]
