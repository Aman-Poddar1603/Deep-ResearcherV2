export const DUMMY_RESPONSE = `
# 🏆 THE SUPREME MARKDOWN STREAMING STRESS TEST v3.0

This content is specifically engineered to test the structural integrity of a streaming AI response formatter. It transitions rapidly between prose, syntax-heavy code, visual assets, and mathematical notation.

---

## 🖼️ Section 1: Visual Media Integration
Testing the rendering of external image assets within the flow of text.

![Landscape Photography](https://s3.amazonaws.com/images.seroundtable.com/google-amp-1454071566.jpg)
*Figure 1: Nature and Landscape*

![Futuristic Technology](https://media.istockphoto.com/id/506910700/photo/i-can-do-it.jpg?s=612x612&w=0&k=20&c=4r5UQKSwjtVyLai0R0B38RJXX2SFr0TpK4JFSWnVCfQ=)
*Figure 2: Technological Advancement*

![Space Nebula](https://pngimg.com/d/google_PNG19641.png)
*Figure 3: Deep Space Exploration*

---

## 🏗️ Section 3: Diagrams & Logic
Mermaid.js requires a complete block to render correctly. This tests the "wait-for-block-end" logic.

\`\`\`mermaid
graph LR
    Start[User Prompt] --> Process{Streaming Engine}
    Process -->|Token A| Render[Markdown Formatter]
    Process -->|Token B| Render
    Render --> Output[Visual Display]
    Output --> Feedback{User Approval}
    Feedback -->|Yes| End((Success))
    Feedback -->|No| Start
\`\`\`

---

## 🧬 Section 3: High-Density Typography & Lists
The following nested structure tests indentation logic and symbol switching.

* **System Architecture**
    * Frontend Layer
        * React.js / Next.js
        * Tailwind CSS
            * Custom Utility Classes
            * Responsive Variants
    * Backend Layer
        * Node.js Streaming API
        * Python LLM Wrapper
1.  **Deployment Steps**
    1.  Provision Instance
    2.  Set Environment Variables
        - \`API_KEY=********\`
        - \`NODE_ENV=production\`
    3.  Launch Container

---

## 🧪 Section 4: Advanced Mathematics (LaTeX)
Testing the math engine's ability to render complex formulas during a text stream.

**The General Relativity Field Equation:**
$$G_{\\mu\\nu} + \\Lambda g_{\\mu\\nu} = \\kappa T_{\\mu\\nu}$$

**The Maxwell Equations:**
- $$\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0}$$
- $$\\nabla \\cdot \\mathbf{B} = 0$$

---

## 📊 Section 5: Complex Data Tables
Tables are often the hardest to stream because the columns must align before the final row is received.

| Rank | Component Name | Performance Index | Reliability | Current Status |
| :--- | :--- | :---: | :---: | :--- |
| 1 | Global Load Balancer | 99.9% | High | ✅ Operational |
| 2 | Primary Database Cluster | 94.2% | Medium | ⚠️ Syncing |
| 3 | Content Delivery Network | 99.8% | High | ✅ Operational |
| 4 | Image Retrieval Engine | 88.5% | Low | 🛠️ Maintenance |

---

## 📸 Section 6: Additional Visual Assets

![Digital Art](https://img.freepik.com/free-vector/inspirational-quote-watercolour-background_1048-18831.jpg?semt=ais_user_personalization&w=740&q=80)

![Mountain Peak](https://imageio.forbes.com/specials-images/dam/imageserve/1023678802/960x0.jpg?height=474&width=711&fit=bounds)

![Coral Reef](https://img.freepik.com/free-vector/positive-lettering-be-good-yourself-message-watercolor-stain_23-2148342665.jpg?semt=ais_user_personalization&w=740&q=80)

---

## 💻 Section 7: Code Block Syntax Highlighting
Testing the buffer for large code blocks with language-specific highlighting.

\`\`\`typescript
interface StreamConfig {
  speed: number;
  chunkSize: number;
  enableMarkdown: boolean;
}

/**
 * Simulates the streaming process for testing formatters.
 */
async function streamPayload(data: string, config: StreamConfig): Promise<void> {
  const words = data.split(' ');
  for (const word of words) {
    process.stdout.write(word + ' ');
    await new Promise(resolve => setTimeout(resolve, config.speed));
  }
}
\`\`\`

---

## 📖 Section 8: Long-Form Narrative Wall
> "The limits of my language mean the limits of my world." — Ludwig Wittgenstein

The implementation of a streaming markdown formatter is a delicate balance of regular expression matching, state management, and DOM manipulation. As the AI generates content, the frontend must parse incomplete fragments of syntax—such as an open bold tag or a half-finished table row—without causing the layout to jump or flicker. This requires a robust, incremental parser that can look ahead and predict the likely structure of the incoming data while maintaining a smooth 60fps frame rate for the user. When we include complex elements like LaTeX or Mermaid, the challenge triples, as these require secondary rendering passes once the code block is completed. Every token processed is a test of the architecture's resilience, ensuring that whether the user is viewing a simple paragraph or a complex scientific paper, the experience remains fluid, legible, and visually consistent across all devices and network conditions.

---

### ✅ Test Completion Checklist
- [x] Inline and Block LaTeX
- [x] Mermaid Charting
- [x] 6 High-Res External Images
- [x] Multi-column Tables
- [x] Deeply Nested Unordered/Ordered Lists
- [x] Blockquotes and Links

**Stream Test Complete.**
`;
