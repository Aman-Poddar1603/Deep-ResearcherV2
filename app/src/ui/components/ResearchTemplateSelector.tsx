import { useEffect, useState } from 'react'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { ButtonGroup } from '@/components/ui/button-group'
import { ResearchTemplatePreview, TEMPLATE_DETAILS } from '@/ui/pages/settings/ResearchTemplatePreview'
import {
    listResearchStaticTemplates,
    type ResearchTemplateRecordStatic,
} from '@/lib/apis'

interface ResearchTemplateSelectorProps {
    value: string
    onChange: (value: string) => void
    className?: string
}

export function ResearchTemplateSelector({ value, onChange, className }: ResearchTemplateSelectorProps) {
    const [apiTemplates, setApiTemplates] = useState<ResearchTemplateRecordStatic[]>([])

    useEffect(() => {
        let cancelled = false
        void listResearchStaticTemplates({ page: 1, size: 100 })
            .then((res) => {
                if (!cancelled) setApiTemplates(res.items)
            })
            .catch(() => {
                if (!cancelled) setApiTemplates([])
            })
        return () => {
            cancelled = true
        }
    }, [])

    const staticKeys = new Set(Object.keys(TEMPLATE_DETAILS))
    const extraApi = apiTemplates.filter((t) => !staticKeys.has(t.id))

    return (
        <div className={className}>
            <ButtonGroup>
                <Select value={value} onValueChange={onChange}>
                    <SelectTrigger className="w-full bg-background min-w-[200px]">
                        <SelectValue placeholder="Select template" />
                    </SelectTrigger>
                    <SelectContent>
                        {Object.entries(TEMPLATE_DETAILS).map(([key, details]) => (
                            <SelectItem key={key} value={key}>
                                <div className="flex items-center">
                                    <span>{details.title}</span>
                                </div>
                            </SelectItem>
                        ))}
                        {extraApi.map((t) => (
                            <SelectItem key={`api-${t.id}`} value={t.id}>
                                <span>{t.title?.trim() || t.id.slice(0, 8)}</span>
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <ResearchTemplatePreview template={value} />
            </ButtonGroup>
        </div>
    )
}
