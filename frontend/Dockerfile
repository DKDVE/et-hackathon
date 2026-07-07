FROM node:22-slim

WORKDIR /app

# ponytail: skip npm ci in image — WSL Docker SSL flakes; use bind-mounted host node_modules
COPY package.json package-lock.json ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
