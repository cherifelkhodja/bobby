/** @type {import('tailwindcss').Config} */

// Bobby v2 design system — palette OKLCH portée depuis le prototype
// « Bobby v2 - Prototype » (claude.ai/design). Les couleurs sémantiques
// (sur, ink, mut, lin, pri…) référencent des CSS variables définies dans
// src/styles/index.css et basculent automatiquement en mode sombre.
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class', // Controlled via class, with system preference as default
  theme: {
    extend: {
      colors: {
        // Accent « azur » (statique — identique clair/sombre)
        primary: {
          DEFAULT: 'oklch(50% 0.17 262)',
          50: 'oklch(97% 0.015 262)',
          100: 'oklch(94% 0.03 262)',
          200: 'oklch(88% 0.06 262)',
          300: 'oklch(80% 0.09 262)',
          400: 'oklch(76% 0.11 262)',
          500: 'oklch(56% 0.16 262)',
          600: 'oklch(50% 0.17 262)',
          700: 'oklch(44% 0.17 262)',
          800: 'oklch(38% 0.14 262)',
          900: 'oklch(30% 0.07 262)',
        },
        // Neutres ardoise-bleutée v2 (clair 50→300, sombre 700→900)
        gray: {
          50: 'oklch(97% 0.008 255)',
          100: 'oklch(95% 0.008 255)',
          200: 'oklch(92% 0.012 255)',
          300: 'oklch(88% 0.014 256)',
          400: 'oklch(61% 0.025 256)',
          500: 'oklch(52% 0.03 258)',
          600: 'oklch(44% 0.03 258)',
          700: 'oklch(28.5% 0.02 258)',
          800: 'oklch(21% 0.022 258)',
          900: 'oklch(16.5% 0.02 258)',
        },
        success: {
          light: 'oklch(95% 0.04 155)',
          DEFAULT: 'oklch(52% 0.12 155)',
          dark: 'oklch(44% 0.11 155)',
        },
        warning: {
          light: 'oklch(96% 0.045 80)',
          DEFAULT: 'oklch(70% 0.13 78)',
          dark: 'oklch(50% 0.12 70)',
        },
        error: {
          light: 'oklch(95% 0.025 22)',
          DEFAULT: 'oklch(52% 0.19 22)',
          dark: 'oklch(48% 0.18 22)',
        },
        // Tokens sémantiques v2 — basculent avec .dark via CSS variables
        bgc: 'var(--bg)',
        sur: 'var(--sur)',
        srf2: 'var(--srf2)',
        ink: 'var(--ink)',
        mut: 'var(--mut)',
        mut2: 'var(--mut2)',
        lin: 'var(--lin)',
        lin2: 'var(--lin2)',
        pri: 'var(--pri)',
        pris: 'var(--pris)',
        prit: 'var(--prit)',
        redt: 'var(--redt)',
        'amb-bg': 'var(--amb-bg)',
        'amb-fg': 'var(--amb-fg)',
        'blu-bg': 'var(--blu-bg)',
        'blu-fg': 'var(--blu-fg)',
        'ind-bg': 'var(--ind-bg)',
        'ind-fg': 'var(--ind-fg)',
        'red-bg': 'var(--red-bg)',
        'red-fg': 'var(--red-fg)',
        'grn-bg': 'var(--grn-bg)',
        'grn-fg': 'var(--grn-fg)',
        'sla-bg': 'var(--sla-bg)',
        'sla-fg': 'var(--sla-fg)',
      },
      fontFamily: {
        sans: ['Inter var', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        soft: 'var(--shd)',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
