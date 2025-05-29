// workers/edge-proxy.js
// ------------------------------------------------------------
// Capabilities
//   • ?raw=1  (or selector="__raw") → returns raw HTML (text/html)
//   • Interdiscount / Brack: scan all <script type="application/ld+json"> blocks,
//       return first numeric offers.price in { price } JSON
//   • MediaMarkt: regex fallback to find CHF price and return { price }
//   • All successful non‑raw responses: { "price": <string|number|null> }
// ------------------------------------------------------------
export default {
    async fetch(request) {
        const url = new URL(request.url);
        const target = url.searchParams.get("url");
        const selector = url.searchParams.get("selector") ?? "";
        const rawFlag = url.searchParams.get("raw");

        if (!target) {
            return new Response("Missing url parameter", { status: 400 });
        }

        // 1) Fetch upstream
        const resp = await fetch(target, { cf: { cacheTtl: 0 } });
        const html = await resp.text();

        // ---------------- RAW passthrough ----------------
        if (rawFlag === "1" || selector === "__raw" || selector === "") {
            return new Response(html, {
                headers: { "Content-Type": "text/html; charset=utf-8" },
            });
        }

        // 2) JSON‑LD script handling (Interdiscount/Brack). We iterate over *all*
        // <script type="application/ld+json"> blocks until we find a Product
        // with offers.price.
        if (selector.startsWith("script")) {
            const ldRegexG = /<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi;
            let match;
            while ((match = ldRegexG.exec(html)) !== null) {
                try {
                    const data = JSON.parse(match[1].trim());
                    // Handle array wrapper (some sites wrap multiple JSON‑LD objects)
                    const nodes = Array.isArray(data) ? data : [data];
                    for (const node of nodes) {
                        if (node["@type"] === "Product" && node.offers) {
                            if (Array.isArray(node.offers)) {
                                for (const off of node.offers) {
                                    if (off.price !== undefined) {
                                        return new Response(
                                            JSON.stringify({ price: off.price }),
                                            { headers: { "Content-Type": "application/json" } }
                                        );
                                    }
                                }
                            } else if (node.offers.price !== undefined) {
                                return new Response(
                                    JSON.stringify({ price: node.offers.price }),
                                    { headers: { "Content-Type": "application/json" } }
                                );
                            }
                        }
                    }
                } catch (_) {
                    // skip malformed json
                }
            }
            // If we get here, no price found in JSON‑LD scripts
            return new Response("Price not found in JSON‑LD", { status: 404 });
        }

        // 3) MediaMarkt regex fallback
        const spanRegex = /<span[^>]*class="[^"]*sc-e0c7d9f7-0 bPkjPs[^"]*"[^>]*>([^<]+)<\/span>/;
        const spanMatch = html.match(spanRegex);
        const chfRegex = /CHF\s*([0-9]+(?:[.,][0-9]+)?)/;
        const chfMatch = html.match(chfRegex);
        const priceText = spanMatch ? spanMatch[1] : chfMatch ? chfMatch[1] : null;

        if (priceText) {
            const cleaned = priceText.replace(/[^\d.,]/g, "");
            return new Response(
                JSON.stringify({ price: cleaned }),
                { headers: { "Content-Type": "application/json" } }
            );
        }

        return new Response(`No match for selector ${selector}`, { status: 404 });
    },
};