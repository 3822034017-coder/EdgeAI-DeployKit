import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'Geist',
          'SF Pro Display',
          'HarmonyOS Sans SC',
          'MiSans',
          'Segoe UI',
          'PingFang SC',
          'Microsoft YaHei',
          'system-ui',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Consolas', 'monospace'],
      },
      colors: {
        canvas: '#090C12',
        canvas2: '#0D111A',
        surface: '#111722',
        surface2: '#0E141F',
        ink: '#EEF3FA',
        muted: '#8A96A8',
        line: 'rgba(148, 163, 184, 0.14)',
        hairline: 'rgba(255, 255, 255, 0.065)',
        cyan: '#6EDBD5',
        blue: '#82AFFF',
        violet: '#A79BFF',
        amber: '#E7BD68',
        green: '#74D99F',
        red: '#F38181',
      },
      boxShadow: {
        card: '0 18px 55px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255,255,255,0.035)',
        insetline: 'inset 0 1px 0 rgba(255,255,255,0.04)',
      },
    },
  },
  plugins: [],
};

export default config;
