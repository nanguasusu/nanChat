import { cn } from "@/lib/utils"
import { marked } from "marked"
import { memo, useId, useMemo } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkBreaks from "remark-breaks"
import remarkGfm from "remark-gfm"

import { CodeBlock, CodeBlockCode } from "@/components/prompt-kit/code-block"

export type MarkdownProps = {
  children: string
  id?: string
  className?: string
  components?: Partial<Components>
}

function parseMarkdownIntoBlocks(markdown: string): string[] {
  return marked.lexer(markdown).map((token) => token.raw)
}

function extractLanguage(className?: string): string {
  const match = className?.match(/language-(\w+)/)
  return match ? match[1] : "plaintext"
}

const INITIAL_COMPONENTS: Partial<Components> = {
  code: function CodeComponent({ className, children, ...props }) {
    const isInline =
      !props.node?.position?.start.line ||
      props.node?.position?.start.line === props.node?.position?.end.line

    if (isInline) {
      return (
        <code
          className={cn(
            "rounded-sm bg-primary-foreground px-1 font-mono text-sm",
            className,
          )}
          {...props}
        >
          {children}
        </code>
      )
    }

    return (
      <CodeBlock>
        <CodeBlockCode code={String(children)} language={extractLanguage(className)} />
      </CodeBlock>
    )
  },
  pre: function PreComponent({ children }) {
    return <>{children}</>
  },
}

const MemoizedMarkdownBlock = memo(
  function MarkdownBlock({
    content,
    components = INITIAL_COMPONENTS,
  }: {
    content: string
    components?: Partial<Components>
  }) {
    return (
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm, remarkBreaks]}
      >
        {content}
      </ReactMarkdown>
    )
  },
  (previous, next) => previous.content === next.content,
)

MemoizedMarkdownBlock.displayName = "MemoizedMarkdownBlock"

function MarkdownComponent({
  children,
  id,
  className,
  components = INITIAL_COMPONENTS,
}: MarkdownProps) {
  const generatedId = useId()
  const blockId = id ?? generatedId
  const blocks = useMemo(() => parseMarkdownIntoBlocks(children), [children])

  return (
    <div className={className}>
      {blocks.map((block, index) => (
        <MemoizedMarkdownBlock
          components={components}
          content={block}
          key={`${blockId}-block-${index}`}
        />
      ))}
    </div>
  )
}

const Markdown = memo(MarkdownComponent)
Markdown.displayName = "Markdown"

export { Markdown }
