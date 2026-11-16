FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
ARG VITE_DEMO_MODE=false
ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
ARG VITE_ACADEMIC_ML_LAB=false
ENV VITE_ACADEMIC_ML_LAB=$VITE_ACADEMIC_ML_LAB
ARG VITE_ACADEMIC_ML_V4=false
ENV VITE_ACADEMIC_ML_V4=$VITE_ACADEMIC_ML_V4
ARG VITE_ACADEMIC_ML_V6=false
ENV VITE_ACADEMIC_ML_V6=$VITE_ACADEMIC_ML_V6
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
