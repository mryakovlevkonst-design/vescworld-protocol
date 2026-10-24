// Bot API relay for Vesc world uploads where api.telegram.org is blocked.
// Only /bot<token>/<method> is forwarded to Telegram as is; anything else
// answers "no". Nothing is stored or logged here.
export const config = { runtime: 'edge' };

export default async function handler(req) {
  const url = new URL(req.url);
  // vercel.json rewrites every path to /api?p=<path>; a direct call keeps its own.
  const path = '/' + (url.searchParams.get('p') ?? url.pathname.replace(/^\/api\/?/, '')).replace(/^\/+/, '');
  if (!path.startsWith('/bot')) return new Response('no', { status: 404 });
  url.searchParams.delete('p');
  const to = 'https://api.telegram.org' + path + (url.search || '');
  const headers = new Headers(req.headers);
  for (const h of ['host', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto', 'x-real-ip', 'forwarded']) headers.delete(h);
  for (const h of [...headers.keys()]) if (h.startsWith('x-vercel-')) headers.delete(h);
  const hasBody = req.method !== 'GET' && req.method !== 'HEAD';
  return fetch(to, { method: req.method, headers, body: hasBody ? req.body : undefined, duplex: 'half' });
}
