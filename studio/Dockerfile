FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./

# Install dependencies and ensure binaries are in PATH
RUN npm install --legacy-peer-deps && \
    npm install -g vite && \
    ln -s /app/node_modules/.bin/vite /usr/local/bin/vite

# Copy application code
COPY . .

EXPOSE 5173

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
