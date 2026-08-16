/**
 * Design tokens.
 *
 * Dark by default: students film in the evening after school and coaches review
 * at night, so a bright white app is the wrong instrument. The accent is an
 * electric lime that reads as "go" against pitch green, and it is used sparingly
 * — on the streak, the primary action, and nothing else — so it keeps meaning
 * something.
 */

export const colors = {
  bg: '#080C0A',
  surface: '#101714',
  surfaceAlt: '#18211D',
  surfaceHi: '#1F2A25',
  border: '#22302A',
  borderBright: '#33443C',

  text: '#F2F7F4',
  textMuted: '#93A99E',
  textFaint: '#5E7268',

  primary: '#C7F53F',
  primaryDim: '#9ECB2A',
  primarySoft: 'rgba(199, 245, 63, 0.12)',
  onPrimary: '#08120A',

  pitch: '#146B45',

  success: '#3DDC84',
  successSoft: 'rgba(61, 220, 132, 0.14)',
  warning: '#FFB020',
  warningSoft: 'rgba(255, 176, 32, 0.14)',
  danger: '#FF5A5F',
  dangerSoft: 'rgba(255, 90, 95, 0.14)',
  flame: '#FF7A1A',
  info: '#4FC3F7',

  gold: '#FFD54F',
  silver: '#CFD8DC',
  bronze: '#D9884F',

  overlay: 'rgba(0, 0, 0, 0.6)',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 22,
  pill: 999,
} as const;

export const font = {
  display: { fontSize: 34, fontWeight: '800' as const, letterSpacing: -0.8 },
  h1: { fontSize: 26, fontWeight: '800' as const, letterSpacing: -0.5 },
  h2: { fontSize: 20, fontWeight: '700' as const, letterSpacing: -0.3 },
  h3: { fontSize: 17, fontWeight: '700' as const },
  body: { fontSize: 15, fontWeight: '500' as const },
  bodySm: { fontSize: 13, fontWeight: '500' as const },
  label: { fontSize: 12, fontWeight: '700' as const, letterSpacing: 0.8 },
  mono: { fontSize: 13, fontWeight: '600' as const },
} as const;

/** Width of the simulated phone column on desktop. */
export const PHONE_WIDTH = 440;
/** Below this, a browser window is treated as a phone. */
export const PHONE_BREAKPOINT = 640;
/** At or above this, the coach layout gets a persistent sidebar. */
export const DESKTOP_BREAKPOINT = 1024;

export const shadow = {
  card: {
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  glow: {
    shadowColor: colors.primary,
    shadowOpacity: 0.35,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
  },
} as const;

export const theme = { colors, spacing, radius, font, shadow };
export default theme;
