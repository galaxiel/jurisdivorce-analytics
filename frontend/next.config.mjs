/** @type {import('next').NextConfig} */
// BUILD_STATIC=1 → export statique (déploiement web : FastAPI sert le dossier out/)
// sans la variable → comportement standard (dev / npm run start)
const nextConfig = {
  reactStrictMode: true,
  ...(process.env.BUILD_STATIC === "1"
    ? {
        output: "export",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {
        // Dev / npm start (port 3100) : le frontend appelle /api/* en same-origin,
        // Next réécrit vers le backend FastAPI — aucun problème de CORS.
        async rewrites() {
          return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
        },
      }),
};

export default nextConfig;
