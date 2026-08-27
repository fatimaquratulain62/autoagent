import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { TaskPage } from './pages/TaskPage'
import { HistoryPage } from './pages/HistoryPage'
import { ScheduledPage } from './pages/ScheduledPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/task/:id" element={<TaskPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/scheduled" element={<ScheduledPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
