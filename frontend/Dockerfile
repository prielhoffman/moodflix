# React + Vite frontend (Node 22+ required for Vite/Rolldown; node:util styleText)
FROM node:22-alpine

WORKDIR /app

# Install dependencies (cached until package files change)
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the frontend code
COPY . .

EXPOSE 5173

# --host is required for Docker to accept connections from outside the container
CMD ["npm", "run", "dev", "--", "--host"]
