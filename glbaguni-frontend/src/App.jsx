import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useTheme } from "./hooks/useTheme";
import { useToast } from "./hooks/useToast";
import Navbar from "./components/Navbar";
import ThemeToggle from "./components/ThemeToggle";
import ToastContainer from "./components/ToastContainer";
import HomePage from "./pages/HomePage";
import SummarizePage from "./pages/SummarizePage";
import HistoryPage from "./pages/HistoryPage";
import RecommendationPage from "./pages/RecommendationPage";
import ContactPage from "./pages/ContactPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import SourcesPage from "./pages/SourcesPage";
import ComponentTestPage from "./pages/ComponentTestPage";

function App() {
  const { theme, toggleTheme } = useTheme();
  const { toasts, removeToast } = useToast();

  return (
    <Router>
      <div className={`min-h-screen ${theme === "dark" ? "dark" : ""}`}>
        <div className="bg-white dark:bg-gray-900 min-h-screen transition-colors duration-200">
          <Navbar />

          <div className="fixed top-4 right-4 z-40">
            <ThemeToggle />
          </div>

          {/* 토스트 컨테이너 */}
          <ToastContainer toasts={toasts} removeToast={removeToast} />

          <main id="main-content">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/summarize" element={<SummarizePage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/recommendations" element={<RecommendationPage />} />
              <Route path="/sources" element={<SourcesPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/test" element={<ComponentTestPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
