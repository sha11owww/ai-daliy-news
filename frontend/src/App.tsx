import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Article from './pages/Article'

export default function App() {
  return (
    <div className="min-h-screen bg-paper">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/article/:id" element={<Article />} />
      </Routes>
    </div>
  )
}
