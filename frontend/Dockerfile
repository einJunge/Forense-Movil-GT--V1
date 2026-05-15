FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Vite dev server escuchando en todas las interfaces
CMD ["npm", "run", "dev"]
