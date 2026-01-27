import { useTheme } from "./theme-provider"

function useLogo() {
  const { isDark } = useTheme()
  return isDark ? "/brand/DeepResearcher-Dark.png" : "/brand/DeepResearcher-Light.png"
}

function useInternalLogo() {
  const { isDark } = useTheme()
  return isDark ? "/brand/inner_logo_dr_dark.png" : "/brand/inner_logo_dr_light.png"
}

export { useLogo, useInternalLogo }