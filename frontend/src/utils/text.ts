export function cleanMarkdownText(text: string | null | undefined): string {
  return (text ?? "")
    .replace(/^[ \t]*#{1,6}[ \t]*/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*\n]+)\*/g, "$1")
    .replace(/^[ \t]*[-*][ \t]+/gm, "")
    // Sweep any stray asterisks left over from unbalanced bold/italic markers
    // (e.g. backend prose that contains "**Весы**" but where a downstream
    // dropcap split strips the first char, leaving "*Весы**" to leak through).
    .replace(/\*+/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
