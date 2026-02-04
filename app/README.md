# 🧠 Deep Researcher

Deep Researcher is a high-performance, desktop-native research platform designed to automate and augment complex inquiry. Built with a focus on depth, speed, and analytical precision, it provides researchers with an AI-powered environment to conduct thorough investigations, manage multi-step research plans, and extract verifiable insights.

![Deep Researcher Banner](public/brand/inner_logo_dr_light.png)

## ✨ Features

- **Autonomous Research Agents**: Deploy agents capable of multi-step reasoning, browsing, and synthesis.
- **Chain-of-Thought Visualization**: Transparently follow the agent's logic and planning process in real-time.
- **Dynamic Research Artifacts**: Capture findings and structured data in high-fidelity artifacts for later use.
- **Workspace-First Architecture**: Organize investigations into dedicated workspaces with persistent context.
- **Inline Citations & Verifiability**: Every claim is backed by citations, ensuring research integrity.
- **Premium UI/UX**: A state-of-the-art interface built with **React 19**, **Tailwind CSS 4**, and **Framer Motion**.
- **Cross-Platform**: Native desktop experience for Windows, macOS, and Linux.

## 🛠️ Technology Stack

- **Core**: [Electron](https://www.electronjs.org/) & [Vite](https://vitejs.dev/)
- **Frontend**: [React 19](https://react.dev/)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/) & [Shadcn UI](https://ui.shadcn.com/)
- **Animations**: [Motion](https://motion.dev/) & [Rive](https://rive.app/)
- **Markdown & Syntax**: [Streamdown](https://github.com/streamdown/streamdown) & [Shiki](https://shiki.style/)
- **Icons**: [Lucide React](https://lucide.dev/)

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (Latest LTS)
- npm or pnpm

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/pixelThreaderOfficial/Deep-Researcher.git
    cd deep-researcher/app
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Environment Setup**:
    Copy `.env.example` to `.env` and configure your API keys:
    ```bash
    cp .env.example .env
    ```

4.  **Run in Development Mode**:
    ```bash
    npm run dev
    ```

## 📦 Distribution

To build the production-ready application for your platform:

- **Windows**: `npm run dist:win`
- **macOS**: `npm run dist:mac`
- **Linux**: `npm run dist:linux`

Builds will be available in the `dist/` directory.

## 📁 Project Structure

```text
app/
├── src/
│   ├── electron/      # Main process & IPC logic
│   ├── ui/            # React frontend
│   │   ├── components/ # Shared UI components
│   │   ├── pages/      # View layouts (Home, Research, etc.)
│   │   └── themes.css  # Design system tokens
│   ├── components/    # Specialized AI & Agent elements
│   └── hooks/         # Custom React hooks
├── public/            # Static assets
└── electron-builder.json # Packaging configuration
```

## 🤝 Contributing

We welcome contributions! Please feel free to submit issues or pull requests to help improve Deep Researcher.

---

<p align="center">
  Developed with ❤️ by <a href="https://github.com/pixelThreaderOfficial">pixelThreader</a>
</p>