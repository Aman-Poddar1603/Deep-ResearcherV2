import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Eye, FileSearch, GraduationCap, BarChart3, Binary, Columns2, Zap, Edit3, Save } from 'lucide-react'
import { useState, useMemo, useEffect } from 'react'
import { PromptEditor } from '@/components/ui/prompt-editor'
import {
    Message,
    MessageContent,
    MessageResponse,
} from "@/components/ai-elements/message"

interface ResearchTemplatePreviewProps {
    template: string
    trigger?: React.ReactNode
}

export const TEMPLATE_DETAILS = {
    comprehensive: {
        title: 'Comprehensive Research',
        description: 'A deep, all-encompassing investigation covering background, current state, and future outlook.',
        icon: <FileSearch className="size-5 text-blue-500" />,
        steps: [
            'Initial broad discovery',
            'Historical context analysis',
            'Cross-reference multiple sources',
            'Synthesize multi-perspective summary',
            'Identify key trends and patterns'
        ],
        estimatedTime: '15-20 mins',
        depth: 'Deep'
    },
    'quick-summary': {
        title: 'Quick Summary',
        description: 'Rapid analysis designed to give you the most important facts and takeaways in minutes.',
        icon: <Zap className="size-5 text-yellow-500" />,
        steps: [
            'Targeted keyword search',
            'Extract key takeaways only',
            'Verify top 3 sources',
            'Bulleted summary generation'
        ],
        estimatedTime: '3-5 mins',
        depth: 'Surface'
    },
    academic: {
        title: 'Academic Study',
        description: 'Focuses on scholarly sources, peer-reviewed journals, and formal research methodologies.',
        icon: <GraduationCap className="size-5 text-purple-500" />,
        steps: [
            'Scholarly database indexing',
            'Methodology evaluation',
            'Citation analysis',
            'Theoretical framework mapping',
            'Formal academic synthesis'
        ],
        estimatedTime: '20-30 mins',
        depth: 'Very Deep'
    },
    'market-analysis': {
        title: 'Market Analysis',
        description: 'Analyzes industry trends, competitor movements, and economic indicators.',
        icon: <BarChart3 className="size-5 text-green-500" />,
        steps: [
            'Competitor landscape mapping',
            'Market size estimation',
            'SWOT analysis generation',
            'Consumer trend identification',
            'Pricing and strategy review'
        ],
        estimatedTime: '15-25 mins',
        depth: 'Medium'
    },
    'technical-deep-dive': {
        title: 'Technical Deep Dive',
        description: 'Focuses on implementation details, specifications, and low-level technical documentation.',
        icon: <Binary className="size-5 text-red-500" />,
        steps: [
            'Technical doc crawling',
            'Architecture review',
            'Code example extraction',
            'Performance benchmark analysis',
            'Ecosystem compatibility check'
        ],
        estimatedTime: '15-25 mins',
        depth: 'Very Deep'
    },
    'comparative': {
        title: 'Comparative Study',
        description: 'Directly compares two or more subjects, highlighting differences, similarities, and trade-offs.',
        icon: <Columns2 className="size-5 text-cyan-500" />,
        steps: [
            'Identify comparison criteria',
            'Parallel data extraction',
            'Side-by-side analysis',
            'Pros and cons mapping',
            'Winning criteria justification'
        ],
        estimatedTime: '10-15 mins',
        depth: 'Medium'
    }
}

export const ResearchTemplatePreview = ({ template, trigger }: ResearchTemplatePreviewProps) => {
    const details = TEMPLATE_DETAILS[template as keyof typeof TEMPLATE_DETAILS] || TEMPLATE_DETAILS.comprehensive

    const [isEditing, setIsEditing] = useState(false)
    const [content, setContent] = useState('')

    // Generate a rich, illustrative markdown artifact for a Bali trip research
    const travelMarkdown = useMemo(() => {
        return `# 🌴 Research Report: Ultimate Bali Expedition 2026

I have conducted a comprehensive deep research into your upcoming trip to Bali. Below is the synthesized intelligence regarding your itinerary, essentials, and cultural immersion.

---

## 📍 Premier Destinations & Landmarks

Bali offers a diverse range of experiences from lush jungles to pristine coastlines. My research highlights these must-visit locations:

### 1. Ubud: The Cultural Heart
*   **Tegalalang Rice Terrace:** Iconic terraced landscapes perfect for morning photography.
*   **Monkey Forest:** A sanctuary for Balinese long-tailed monkeys and ancient temple structures.

**Visual Atmosphere:**
------

![Ubud Tropical Lushness](https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=400&q=80)
![Ubud Forest](https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?auto=format&fit=crop&w=400&q=80)
![Ubud Palace](https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=400&q=80)

------

### 2. Uluwatu: Cliffside Majesty
Famous for its high-altitude temples and world-class surfing breaks.
*   **Uluwatu Temple:** Catch the Kecak Fire Dance at sunset.

**Visual Atmosphere:**
----
![Uluwatu Sunset](https://images.unsplash.com/photo-1539367628448-4bc5c9d171c8?auto=format&fit=crop&w=400&q=80)
![Uluwatu Temple Cliff](https://images.unsplash.com/photo-1552074284-5e88ef1aef18?auto=format&fit=crop&w=400&q=80)
![Uluwatu Waves](https://images.unsplash.com/photo-1501179691627-eeaa65ea017c?auto=format&fit=crop&w=400&q=80)

---

## 🎬 Local Insights & Vlogs

Explore the vibe of Bali through these highly-rated travel guides:

### Essential Bali Guide
----

<iframe width="560" height="315" src="https://www.youtube.com/embed/2q91J52NFGs?si=4at0ux05KTy4-lmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### Bali Tour | Bali Tourist Places | Bali Indonesia | Bali Travel Guide | Bali | Nusa Penida #bali
This video can give you glimpse of the trip to bali.

-----

<iframe width="560" height="315" src="https://www.youtube.com/embed/2q91J52NFGs?si=4at0ux05KTy4-lmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
<iframe width="560" height="315" src="https://www.youtube.com/embed/2q91J52NFGs?si=4at0ux05KTy4-lmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
<iframe width="560" height="315" src="https://www.youtube.com/embed/2q91J52NFGs?si=4at0ux05KTy4-lmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
<iframe width="560" height="315" src="https://www.youtube.com/embed/2q91J52NFGs?si=4at0ux05KTy4-lmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

----
---

## 👕 Packing & Essential Clothing

Based on the climate and cultural norms, I recommend the following:

### 🌞 Day Gear (Light & Breathable)
*   **Linen Shirts & Shorts:** Humidity is high; focus on natural fibers.
*   **Swimwear:** Essential for beach club hopping in Canggu or Seminyak.
*   **Footwear:** Comfortable walking sandals for temple tours.


**Example Style:**
-----

![Bali Summer Wear](https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=400&q=80)
![Bali Beach Style](https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=400&q=80)


### ⛩️ Temple Etiquette
*   **Sarong:** Required for entry to all sacred sites. A colorful light sarong is recommended.
*   **Shoulder Coverings:** Modest tops are a sign of respect.

---

## � Visual Gallery
Explore the diverse landscapes of Bali in this curated collection of high-resolution captures:

![Temple](https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?auto=format&fit=crop&w=300&q=80)
![Coast](https://images.unsplash.com/photo-1552074284-5e88ef1aef18?auto=format&fit=crop&w=300&q=80)
![Jungle](https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=300&q=80)
![Waterfall](https://images.unsplash.com/photo-1501179691627-eeaa65ea017c?auto=format&fit=crop&w=300&q=80)
![Resort](https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=300&q=80)

---

## �🗺️ Smart Research Summary
This report was synthesized using the **${details.title}** template. 
- **Searches Conducted:** 42 distinct queries
- **Sources Verified:** Scholarly travel journals, local Indonesian government portals, and verified tourist reviews.
- **Synthesized by:** Deep Researcher AI Engine`
    }, [details])

    useEffect(() => {
        setContent(travelMarkdown)
    }, [travelMarkdown])

    return (
        <Sheet onOpenChange={(open) => { if (!open) setIsEditing(false) }}>
            <SheetTrigger asChild>
                {trigger || (
                    <Button variant="outline" size="icon" className="shrink-0">
                        <Eye className="size-4" />
                    </Button>
                )}
            </SheetTrigger>
            <SheetContent className="w-full sm:w-1/2 sm:max-w-none border-l border-border/50 bg-card/95 backdrop-blur-xl p-0 flex flex-col overflow-hidden">
                <div className="flex-1 overflow-y-auto px-8 pt-8 pb-32">
                    <SheetHeader className="space-y-4 p-0">
                        <div className="flex items-center gap-4">
                            <div className="size-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                                {details.icon}
                            </div>
                            <div>
                                <SheetTitle className="text-xl font-bold">{details.title}</SheetTitle>
                                <SheetDescription className="text-sm">
                                    {isEditing ? "Customize this template's execution instructions." : details.description}
                                </SheetDescription>
                            </div>
                        </div>
                    </SheetHeader>

                    <div className="mt-8">
                        {isEditing ? (
                            <div className="rounded-2xl border border-border bg-background overflow-hidden p-1 shadow-inner group focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                                <PromptEditor
                                    value={content}
                                    onChange={setContent}
                                    placeholder="Define how this research template should operate..."
                                    className="bg-transparent border-none focus:ring-0 min-h-[500px]"
                                />
                            </div>
                        ) : (
                            <div className="space-y-6">
                                <div className="rounded-2xl border border-border bg-background p-6 shadow-sm">
                                    <Message from="assistant" className="max-w-none w-full">
                                        <MessageContent className="max-w-none w-full bg-transparent p-0 text-base leading-relaxed">
                                            <MessageResponse>
                                                {content}
                                            </MessageResponse>
                                        </MessageContent>
                                    </Message>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="shrink-0 p-8 border-t bg-background/50 backdrop-blur-xl flex items-center justify-between gap-4 absolute bottom-0 left-0 right-0">
                    <Button
                        variant="ghost"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => setIsEditing(false)}
                    >
                        Close Preview
                    </Button>

                    <div className="flex items-center gap-3">
                        <Button
                            variant="outline"
                            onClick={() => setIsEditing(!isEditing)}
                            className="gap-2 border-primary/20 hover:bg-primary/5 hover:text-primary transition-colors"
                        >
                            {isEditing ? (
                                <><Eye className="size-4" /> Preview Mode</>
                            ) : (
                                <><Edit3 className="size-4" /> Edit Template</>
                            )}
                        </Button>
                        <Button className="gap-2 shadow-lg shadow-primary/20">
                            <Save className="size-4" />
                            Save Config
                        </Button>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    )
}
