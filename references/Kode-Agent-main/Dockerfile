# Build stage
FROM node:22-alpine AS builder

# Configure Alpine to use China mirrors
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# Install build dependencies
RUN apk add --no-cache \
    bash \
    git \
    python3 \
    py3-pip \
    make \
    g++ \
    curl

# Configure npm to use China registry
RUN npm config set registry https://registry.npmmirror.com/

# Configure pip to use Tsinghua mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Install bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install pnpm and dependencies
RUN npm install -g pnpm && \
    pnpm config set registry https://registry.npmmirror.com/ && \
    pnpm install

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Verify files exist after build
RUN ls -la /app/

# Runtime stage
FROM node:22-alpine AS runtime

# Configure Alpine to use China mirrors
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# Install only runtime dependencies
RUN apk add --no-cache \
    bash \
    curl

# Configure npm to use China registry
RUN npm config set registry https://registry.npmmirror.com/

# Install bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# Install tsx globally since it's needed at runtime
RUN npm install -g tsx

# Create workspace directory
WORKDIR /workspace

# Copy built application from builder stage
COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/src /app/src

# Create the entrypoint script
# RUN cat << 'EOF' > /entrypoint.sh
# #!/bin/sh
 
# /root/.bun/bin/bun /app/dist/entrypoints/cli.js -c /workspace "$@"
# EOF

# RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/root/.bun/bin/bun", "/app/dist/entrypoints/cli.js", "-c", "/workspace"]
