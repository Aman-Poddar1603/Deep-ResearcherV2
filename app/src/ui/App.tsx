import { HashRouter, Routes, Route } from "react-router-dom"
import { Layout } from "./Layout"
import { Home } from "./pages/Home"
import "./App.css"

function App() {
    return (
        <HashRouter>
            <Routes>
                <Route element={<Layout />}>
                    <Route index element={<Home />} />
                    {/* Add more routes here as needed */}
                </Route>
            </Routes>
        </HashRouter>
    )
}

export default App
