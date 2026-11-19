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
    : {}),
};

export default nextConfig;
