export function insertAtCursor(
  element: HTMLInputElement | HTMLTextAreaElement | null,
  value: string,
  text: string,
  setValue: (value: string) => void,
): void {
  const start = element?.selectionStart ?? value.length
  const end = element?.selectionEnd ?? value.length
  const caret = start + text.length
  setValue(value.slice(0, start) + text + value.slice(end))
  requestAnimationFrame(() => {
    element?.focus()
    element?.setSelectionRange(caret, caret)
  })
}
