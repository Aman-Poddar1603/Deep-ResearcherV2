import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { ButtonGroup } from '@/components/ui/button-group'
import { ResearchTemplatePreview, TEMPLATE_DETAILS } from '@/ui/pages/settings/ResearchTemplatePreview'

interface ResearchTemplateSelectorProps {
    value: string
    onChange: (value: string) => void
    className?: string
}

export function ResearchTemplateSelector({ value, onChange, className }: ResearchTemplateSelectorProps) {
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
                    </SelectContent>
                </Select>
                <ResearchTemplatePreview template={value} />
            </ButtonGroup>
        </div>
    )
}
