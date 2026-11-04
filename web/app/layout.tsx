import type {Metadata} from "next";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";
import "./globals.css";

export const metadata: Metadata = {title: "Housing Finance GPS — comparação sintética", description: "Comparação local de moradia com premissas explícitas e motor financeiro determinístico."};
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {return <html lang="pt-BR"><body>{children}</body></html>;}
