/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    AWS_REGION: process.env.AWS_REGION,
    S3_BUCKET_NAME: process.env.S3_BUCKET_NAME,
  },
  webpack: (config, { isServer }) => {
    // Externalize ws library to prevent bundling issues
    if (isServer) {
      config.externals.push({
        'ws': 'commonjs ws',
        'bufferutil': 'commonjs bufferutil',
        'utf-8-validate': 'commonjs utf-8-validate',
      })
    }
    
    // Ignore optional dependencies
    config.resolve.fallback = {
      ...config.resolve.fallback,
      'bufferutil': false,
      'utf-8-validate': false,
    }
    
    return config
  },
  // Increase serverComponentsExternalPackages for ws
  serverComponentsExternalPackages: ['ws'],
}

module.exports = nextConfig




