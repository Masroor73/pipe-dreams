// Wake and sleep phrase matching for the hands-free voice copilot. Pure functions.
const norm = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const WAKE = /\b(hello|hey|hi|okay|ok)\s+(co\s?pilot|copilot|co pilot|pipe\s?dreams?)\b/;
const BYE = /\b(bye|goodbye|good bye|stop)\s+(co\s?pilot|copilot|co pilot|pipe\s?dreams?)\b/;

export function matchesWake(text: string): boolean {
  return WAKE.test(norm(text));
}

export function matchesBye(text: string): boolean {
  return BYE.test(norm(text));
}
