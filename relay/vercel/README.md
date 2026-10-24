# Bot API relay on Vercel

For displays where `api.telegram.org` is blocked (Russia). It forwards
`/bot<token>/<method>` to Telegram unchanged and answers `no` to anything
else. Nothing is stored or logged. The same job as the Cloudflare Worker in
the MLTRA manual, on a different network - try it when Cloudflare is slow or cut.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fmryakovlevkonst-design%2Fvescworld-protocol%2Ftree%2Fmain%2Frelay%2Fvercel&project-name=vw-relay&repository-name=vw-relay)

1. Press the button, sign in to Vercel (with GitHub), press **Create**.
2. When it says *Congratulations*, open the project: the address is under
   **Domains**, like `vw-relay-xxxx.vercel.app`.
3. Open the address in a browser: it must say `no`.
4. Put the address into the display: `/setup` in @vescworldbot, card 4, or
   `tgapi vw-relay-xxxx.vercel.app` over USB.

Free Hobby plan; a request body is limited to 4.5 MB (display files are far smaller).
