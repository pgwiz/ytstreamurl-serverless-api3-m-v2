# Layout & Styling Guide 🎨

**Purpose:** This document serves as a reference for AI agents to replicate the visual style of the `ytstreamurl-serverless` project documentation and playground.

---

## 1. Core Resources

The design relies on **Tailwind CSS** (via CDN) and **Google Fonts**.

### Head Includes
```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Typography: Inter -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<!-- Lucide Icons (Used in Playground) -->
<script src="https://unpkg.com/lucide@latest"></script>
```

---

## 2. Design System

### 🌑 Color Palette (Dark Mode)

| Element | Tailwind Class | Hex/Description |
|---------|----------------|-----------------|
| **Page Background** | `bg-gray-900` | Very dark gray/black |
| **Card Background** | `bg-gray-800` | Dark gray overlay |
| **Text Primary** | `text-white` | Pure white |
| **Text Secondary** | `text-gray-400` | Muted text |
| **Text Accent** | `text-gray-500` | Subtle labels/footers |

### 🖋️ Typography

- **Font Family:** `Inter`, sans-serif
- **Headings:** Bold (`font-bold`), typically `text-xl` or `text-2xl`.
- **Code:** Monospace, colored (Yellow/Green/Blue for syntax highlighting).

### 🌈 Gradients & Accents

Used for titles, banners, and buttons to add vibrancy.

- **Main Title Gradient:** `linear-gradient(135deg, #1e3a8a, #3b82f6, #9333ea)` (Blue to Purple)
  - Class: `.gradient-bg` (Custom CSS)
- **Playground Banner:** `bg-gradient-to-r from-blue-600 to-purple-600`
- **Method Badges:** `bg-green-500 text-black` (e.g., GET)

---

## 3. Custom CSS

Add this `<style>` block to `index.html`:

```css
<style>
    body {
        font-family: 'Inter', sans-serif;
    }

    /* Main Title Text Gradient */
    .gradient-bg {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6, #9333ea);
    }
    
    /* Code Block Scrollbars (Firefox/Standard) */
    pre {
        scrollbar-width: thin;
        scrollbar-color: #4b5563 #1f2937;
    }
    
    /* Chrome/Safari Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1f2937; 
    }
    ::-webkit-scrollbar-thumb {
        background: #4b5563; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #6b7280; 
    }
</style>
```

---

## 4. Component Patterns

### 📦 Content Card
Standard container for sections.

```html
<div class="bg-gray-900 rounded-xl p-5">
    <h2 class="text-xl font-semibold mb-3 text-blue-400">Section Title</h2>
    <div class="space-y-3">
        <!-- Content -->
    </div>
</div>
```

### 🔗 Endpoint Item (Clickable/Hoverable)
Used for listing API endpoints.

```html
<div class="bg-gray-800 p-3 rounded-lg hover:bg-gray-700 transition">
    <span class="bg-green-500 text-xs px-2 py-1 rounded font-bold text-black">GET</span>
    <code class="text-yellow-300 ml-2">/path/to/endpoint</code>
    <p class="text-gray-400 mt-1 text-sm">Description of endpoint</p>
</div>
```

### 💻 Code Block
Used for JSON responses.

```html
<pre class="bg-gray-800 text-xs text-green-300 p-4 rounded-lg overflow-x-auto border border-gray-700"><code>{
  "key": "value"
}</code></pre>
```

---

## 5. Layout Structure

### Main Container
Centered, max-width, with padding.
```html
<body class="bg-gray-900 text-white min-h-screen p-4">
    <div class="max-w-6xl mx-auto">
        <div class="bg-gray-800 rounded-2xl shadow-2xl overflow-hidden">
             <!-- Page Content -->
        </div>
    </div>
</body>
```

### Two-Column Grid
Responsive grid: 1 column on mobile, 2 columns on large screens.
```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Left Column -->
    <div class="space-y-6">...</div>
    
    <!-- Right Column -->
    <div class="space-y-6">...</div>
</div>
```

---

## 6. Glassmorphism (Playground Only)
The Playground app uses a slightly different "Glass" aesthetic.

```css
.glass-panel {
    background: rgba(31, 41, 55, 0.7); /* gray-800 with opacity */
    backdrop-filter: blur(10px);
    border: 1px solid rgba(75, 85, 99, 0.4); /* gray-600 with opacity */
}
```
