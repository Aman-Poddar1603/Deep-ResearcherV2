import { HashRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/ui/Layout"
import "./App.css"

import { Home } from "@/ui/pages/Home"

// Workspaces
import { CreateWorkspace, AllWorkspaces, EditWorkspace, ViewWorkspace } from "@/ui/pages/workspaces"

// Data / Store
import { Databases, Tables, DataVisualizer, Bucket, BucketItems } from "@/ui/pages/store"

// History
import { History } from "@/ui/pages/history"

// Settings
import { Settings } from "@/ui/pages/settings"
import NotFound from "@/ui/pages/settings/NotFound"

// Research Pages
import { AllResearches, NewResearch } from "@/ui/pages/Research"

// Chat Pages
import { ChatInterface, Chats } from "@/ui/pages/chats"

function App() {
    return (
        <HashRouter>
            <Routes>
                <Route element={<Layout />}>
                    <Route index element={<Home />} />

                    {/* Workspaces Routes */}
                    <Route path="/workspaces/new" element={<CreateWorkspace />} />
                    <Route path="/workspaces/all" element={<AllWorkspaces />} />
                    <Route path="/workspaces/edit/:id" element={<EditWorkspace />} />
                    <Route path="/workspaces/view/:id" element={<ViewWorkspace />} />

                    {/* Research Routes - TODO: Create these pages */}
                    <Route path="/researches/new" element={<NewResearch />} />
                    <Route path="/researches/all" element={<AllResearches />} />

                    {/* Chat Routes - TODO: Create these pages */}
                    <Route path="/chat/new" element={<ChatInterface />} />
                    <Route path="/chat/all" element={<Chats />} />

                    {/* Data / Store Routes */}
                    <Route path="/data/databases" element={<Databases />} />
                    <Route path="/data/databases/:id/tables" element={<Tables />} />
                    <Route path="/data/databases/:id/visualizer" element={<DataVisualizer />} />
                    <Route path="/data/bucket" element={<Bucket />} />
                    <Route path="/data/bucket/:bucketId" element={<BucketItems />} />

                    {/* History Route */}
                    <Route path="/history" element={<History />} />

                    {/* Settings Route */}
                    <Route path="/settings" element={<Settings />} />

                    {/* 404 Route */}
                    <Route path="*" element={<NotFound />} />
                </Route>
            </Routes>
        </HashRouter>
    )
}

export default App
