import { useWindowDimensions } from 'react-native';

import { DESKTOP_BREAKPOINT, PHONE_BREAKPOINT } from '@/theme';

export type Responsive = {
  width: number;
  height: number;
  /** True when the viewport is physically phone-sized. */
  isNarrow: boolean;
  /** True when there is room for the coach's sidebar layout. */
  isDesktop: boolean;
  /** True when a phone-shaped column should be simulated inside a big window. */
  simulatePhone: boolean;
};

export function useResponsive(): Responsive {
  const { width, height } = useWindowDimensions();
  const isNarrow = width < PHONE_BREAKPOINT;
  return {
    width,
    height,
    isNarrow,
    isDesktop: width >= DESKTOP_BREAKPOINT,
    simulatePhone: !isNarrow,
  };
}
