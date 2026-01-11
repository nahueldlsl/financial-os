export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}", // <--- ESTA LINEA ES VITAL
    ],
    theme: {
        extend: {
            colors: {
                slate: {
                    800: '#1e293b', // Colores personalizados para el tema oscuro
                    900: '#0f172a',
                    950: '#020617',
                }
            }
        },
    },
    plugins: [],
}
