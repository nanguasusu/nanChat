export const DESKTOP_MEDIA_QUERY = "(min-width: 768px)"

export function isDesktopViewport() {
  return window.matchMedia(DESKTOP_MEDIA_QUERY).matches
}
