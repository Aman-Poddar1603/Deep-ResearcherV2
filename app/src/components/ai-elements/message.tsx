"use client";

import { Button } from "src/components/ui/button";
import {
  ButtonGroup,
  ButtonGroupText,
} from "src/components/ui/button-group";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "src/components/ui/tooltip";
import { cn } from "src/lib/utils";
import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { math } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";
import type { UIMessage } from "ai";
import { ChevronLeftIcon, ChevronRightIcon, Eye, Download } from "lucide-react";
import type { ComponentProps, HTMLAttributes, ReactElement } from "react";
import { createContext, memo, useContext, useEffect, useMemo, useState, Children, isValidElement } from "react";
import { Streamdown, defaultRehypePlugins } from "streamdown";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"];
};

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full max-w-[95%] flex-col gap-2",
      from === "user" ? "is-user ml-auto justify-end" : "is-assistant",
      className
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "is-user:dark flex w-fit min-w-0 max-w-full flex-col gap-2 overflow-hidden text-sm",
      "group-[.is-user]:ml-auto group-[.is-user]:rounded-lg group-[.is-user]:bg-secondary group-[.is-user]:px-4 group-[.is-user]:py-3 group-[.is-user]:text-secondary-foreground",
      "group-[.is-assistant]:text-foreground",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export type MessageActionsProps = ComponentProps<"div">;

export const MessageActions = ({
  className,
  children,
  ...props
}: MessageActionsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props}>
    {children}
  </div>
);

export type MessageActionProps = ComponentProps<typeof Button> & {
  tooltip?: string;
  label?: string;
};

export const MessageAction = ({
  tooltip,
  children,
  label,
  variant = "ghost",
  size = "icon-sm",
  ...props
}: MessageActionProps) => {
  const button = (
    <Button size={size} type="button" variant={variant} {...props}>
      {children}
      <span className="sr-only">{label || tooltip}</span>
    </Button>
  );

  if (tooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
};

interface MessageBranchContextType {
  currentBranch: number;
  totalBranches: number;
  goToPrevious: () => void;
  goToNext: () => void;
  branches: ReactElement[];
  setBranches: (branches: ReactElement[]) => void;
}

const MessageBranchContext = createContext<MessageBranchContextType | null>(
  null
);

const useMessageBranch = () => {
  const context = useContext(MessageBranchContext);

  if (!context) {
    throw new Error(
      "MessageBranch components must be used within MessageBranch"
    );
  }

  return context;
};

export type MessageBranchProps = HTMLAttributes<HTMLDivElement> & {
  defaultBranch?: number;
  onBranchChange?: (branchIndex: number) => void;
};

export const MessageBranch = ({
  defaultBranch = 0,
  onBranchChange,
  className,
  ...props
}: MessageBranchProps) => {
  const [currentBranch, setCurrentBranch] = useState(defaultBranch);
  const [branches, setBranches] = useState<ReactElement[]>([]);

  const handleBranchChange = (newBranch: number) => {
    setCurrentBranch(newBranch);
    onBranchChange?.(newBranch);
  };

  const goToPrevious = () => {
    const newBranch =
      currentBranch > 0 ? currentBranch - 1 : branches.length - 1;
    handleBranchChange(newBranch);
  };

  const goToNext = () => {
    const newBranch =
      currentBranch < branches.length - 1 ? currentBranch + 1 : 0;
    handleBranchChange(newBranch);
  };

  const contextValue: MessageBranchContextType = {
    currentBranch,
    totalBranches: branches.length,
    goToPrevious,
    goToNext,
    branches,
    setBranches,
  };

  return (
    <MessageBranchContext.Provider value={contextValue}>
      <div
        className={cn("grid w-full gap-2 [&>div]:pb-0", className)}
        {...props}
      />
    </MessageBranchContext.Provider>
  );
};

export type MessageBranchContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageBranchContent = ({
  children,
  ...props
}: MessageBranchContentProps) => {
  const { currentBranch, setBranches, branches } = useMessageBranch();
  const childrenArray = useMemo(
    () => (Array.isArray(children) ? children : [children]),
    [children]
  );

  // Use useEffect to update branches when they change
  useEffect(() => {
    if (branches.length !== childrenArray.length) {
      setBranches(childrenArray);
    }
  }, [childrenArray, branches, setBranches]);

  return childrenArray.map((branch, index) => (
    <div
      className={cn(
        "grid gap-2 overflow-hidden [&>div]:pb-0",
        index === currentBranch ? "block" : "hidden"
      )}
      key={branch.key}
      {...props}
    >
      {branch}
    </div>
  ));
};

export type MessageBranchSelectorProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"];
};

export const MessageBranchSelector = ({
  className,
  ...props
}: MessageBranchSelectorProps) => {
  const { totalBranches } = useMessageBranch();

  // Don't render if there's only one branch
  if (totalBranches <= 1) {
    return null;
  }

  return (
    <ButtonGroup
      className={cn(
        "[&>*:not(:first-child)]:rounded-l-md [&>*:not(:last-child)]:rounded-r-md",
        className
      )}
      orientation="horizontal"
      {...props}
    />
  );
};

export type MessageBranchPreviousProps = ComponentProps<typeof Button>;

export const MessageBranchPrevious = ({
  children,
  ...props
}: MessageBranchPreviousProps) => {
  const { goToPrevious, totalBranches } = useMessageBranch();

  return (
    <Button
      aria-label="Previous branch"
      disabled={totalBranches <= 1}
      onClick={goToPrevious}
      size="icon-sm"
      type="button"
      variant="ghost"
      {...props}
    >
      {children ?? <ChevronLeftIcon size={14} />}
    </Button>
  );
};

export type MessageBranchNextProps = ComponentProps<typeof Button>;

export const MessageBranchNext = ({
  children,
  ...props
}: MessageBranchNextProps) => {
  const { goToNext, totalBranches } = useMessageBranch();

  return (
    <Button
      aria-label="Next branch"
      disabled={totalBranches <= 1}
      onClick={goToNext}
      size="icon-sm"
      type="button"
      variant="ghost"
      {...props}
    >
      {children ?? <ChevronRightIcon size={14} />}
    </Button>
  );
};

export type MessageBranchPageProps = HTMLAttributes<HTMLSpanElement>;

export const MessageBranchPage = ({
  className,
  ...props
}: MessageBranchPageProps) => {
  const { currentBranch, totalBranches } = useMessageBranch();

  return (
    <ButtonGroupText
      className={cn(
        "border-none bg-transparent text-muted-foreground shadow-none",
        className
      )}
      {...props}
    >
      {currentBranch + 1} of {totalBranches}
    </ButtonGroupText>
  );
};

const MarkdownImage = ({ className, ...props }: ComponentProps<"img">) => {
  const handlePreview = () => {
    if (props.src) window.open(props.src, "_blank");
  };

  const handleDownload = () => {
    if (props.src) {
      const link = document.createElement("a");
      link.href = props.src;
      link.download = (props.alt as string) || "image";
      link.click();
    }
  };

  return (
    <div className="group/markdown-image relative my-4 flex-none w-fit max-w-full overflow-hidden rounded-xl border border-border/50 shadow-md transition-all hover:shadow-lg snap-start">
      <img
        className={cn(
          "h-[200px] w-auto max-w-none object-contain shrink-0 snap-start",
          className
        )}
        {...props}
      />
      {/* Action Overlay */}
      <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/40 opacity-0 transition-opacity group-hover/markdown-image:opacity-100">
        <Button
          onClick={handlePreview}
          size="icon-xs"
          type="button"
          variant="secondary"
          className="h-8 w-8 rounded-full shadow-lg"
        >
          <Eye size={14} />
        </Button>
        <Button
          onClick={handleDownload}
          size="icon-xs"
          type="button"
          variant="secondary"
          className="h-8 w-8 rounded-full shadow-lg"
        >
          <Download size={14} />
        </Button>
      </div>
    </div>
  );
};

export type MessageResponseProps = ComponentProps<typeof Streamdown>;

export const MessageResponse = memo(
  ({ className, ...props }: MessageResponseProps) => (
    <Streamdown
      className={cn(
        "size-full overflow-x-auto overflow-y-hidden [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      rehypePlugins={useMemo(() => {
        const plugins: NonNullable<MessageResponseProps["rehypePlugins"]> = [];
        if (defaultRehypePlugins.raw) plugins.push(defaultRehypePlugins.raw);

        if (defaultRehypePlugins.sanitize) {
          const sanitizeEntry = defaultRehypePlugins.sanitize;
          const sanitizePlugin = Array.isArray(sanitizeEntry) ? sanitizeEntry[0] : sanitizeEntry;

          plugins.push([sanitizePlugin, {
            tagNames: ['iframe', 'span', 'div', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'hr', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'details', 'summary'],
            attributes: {
              '*': ['className', 'style', 'id'],
              iframe: ['src', 'width', 'height', 'title', 'frameborder', 'allow', 'allowfullscreen', 'referrerpolicy', 'className', 'style'],
              a: ['href', 'target', 'rel'],
              img: ['src', 'alt', 'title', 'width', 'height'],
            }
          }]);
        }

        return plugins;
      }, [])}
      components={{
        // Use div instead of p to avoid hydration errors with nested block elements (like images or tables)
        p: ({ children, className }) => {
          const childrenArray = Children.toArray(children);
          const hasMedia = childrenArray.some(child =>
            isValidElement(child) && (
              child.type === 'img' ||
              child.type === 'iframe' ||
              (typeof child.type === 'string' && child.type === 'a') ||
              (child.props as { src?: string })?.src
            )
          );

          if (hasMedia && childrenArray.length > 1) {
            return (
              <div className={cn("mb-4 last:mb-0 flex gap-4 overflow-x-auto pb-4 scrollbar-hide snap-x items-start", className)}>
                {children}
              </div>
            );
          }
          return <div className={cn("mb-4 last:mb-0", className)}>{children}</div>;
        },
        a: ({ href, children, className }) => {
          const ytMatch = href?.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);

          if (ytMatch) {
            const videoId = ytMatch[1];
            return (
              <div className="w-full my-6">
                <div className="mx-auto w-full max-w-4xl overflow-hidden rounded-xl border border-border/50 shadow-lg transition-all hover:shadow-xl aspect-video">
                  <iframe
                    src={`https://www.youtube.com/embed/${videoId}`}
                    className="w-full h-full bg-muted/20"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  />
                </div>
              </div>
            );
          }

          return <a href={href} className={cn("text-primary hover:underline", className)} target="_blank" rel="noopener noreferrer">{children}</a>;
        },
        // Robust HTML handling for raw <iframe> tags
        html: ({ children, className }) => {
          const content = String(children);
          // Manually extract iframe src if present to render a clean version
          // Handles both raw strings and potentially escaped content
          const iframeMatch = content.match(/<iframe.*?src=["'](.*?)["'].*?>/i) ||
            content.match(/&lt;iframe.*?src=["'](.*?)["'].*?&gt;/i);

          if (iframeMatch) {
            return (
              <div className="w-full my-6">
                <div className="mx-auto w-full max-w-4xl overflow-hidden rounded-xl border border-border/50 shadow-lg transition-all hover:shadow-xl aspect-video">
                  <iframe
                    src={iframeMatch[1]}
                    className={cn("w-full h-full bg-muted/20", className)}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  />
                </div>
              </div>
            );
          }

          if (typeof children === 'string') {
            return (
              <div
                className={cn("my-4 whitespace-normal wrap-break-word", className)}
                dangerouslySetInnerHTML={{ __html: children }}
              />
            );
          }
          return <div className={cn("my-4", className)}>{children}</div>;
        },
        img: ({ className, ...props }) => (
          <MarkdownImage className={className} {...props} />
        ),
        iframe: ({ className, ...props }) => (
          <div className="my-4 flex-none max-w-full overflow-hidden rounded-xl border border-border/50 shadow-md aspect-video snap-start">
            <iframe
              className={cn("w-full h-full bg-muted/20", className)}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              {...props}
            />
          </div>
        )
      }}
      plugins={{ code, mermaid, math, cjk }}
      shikiTheme={['github-light', 'github-dark']}
      {...props}
    />
  ),
  (prevProps, nextProps) =>
    prevProps.children === nextProps.children &&
    prevProps.isAnimating === nextProps.isAnimating &&
    JSON.stringify(prevProps.shikiTheme) === JSON.stringify(nextProps.shikiTheme)
);

MessageResponse.displayName = "MessageResponse";

export type MessageToolbarProps = ComponentProps<"div">;

export const MessageToolbar = ({
  className,
  children,
  ...props
}: MessageToolbarProps) => (
  <div
    className={cn(
      "mt-4 flex w-full items-center justify-between gap-4",
      className
    )}
    {...props}
  >
    {children}
  </div>
);
