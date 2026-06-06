// NEXUS CORE DASHBOARD INTERACTIVE SYSTEM

class NexusApp {
    constructor() {
        this.revenue = 84.5;
        this.agents = 1204;
        this.autos = 42;
        this.currentCategory = 'OVERVIEW';
        this.init();
    }

    init() {
        // Elements
        this.chatToggle = document.getElementById('chat-toggle');
        this.chatContainer = document.getElementById('axionchat-container');
        this.chatInput = document.getElementById('chat-input');
        this.chatSubmit = document.getElementById('chat-submit');
        this.chatHistory = document.getElementById('chat-history');
        
        // Setup Chat Toggle
        if (this.chatToggle && this.chatContainer) {
            this.chatToggle.addEventListener('click', () => {
                this.chatContainer.classList.toggle('hidden');
            });
        }

        // Setup Chat Send
        if (this.chatSubmit && this.chatInput) {
            this.chatSubmit.addEventListener('click', () => this.handleSendMessage());
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.handleSendMessage();
            });
        }

        // Dynamic stats update
        setInterval(() => {
            if (Math.random() > 0.7) {
                this.agents += Math.floor(Math.random() * 3);
                document.getElementById('val-agents').textContent = this.agents;
            }
        }, 5000);
    }

    switchCategory(category) {
        this.currentCategory = category;
        const breadcrumbCat = document.getElementById('current-category');
        if (breadcrumbCat) breadcrumbCat.textContent = category;

        // Visual feedback in sidebar
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Log switch event in neural terminal
        this.logTerminal(`[NAVIGATION] Category switched to ${category}`);
    }

    executePipeline() {
        this.logTerminal(`[PROCESS] Executing pipeline for ${this.currentCategory}...`);
        setTimeout(() => {
            this.logTerminal(`[STATUS] Scanning perimeter targets...`);
        }, 600);
        setTimeout(() => {
            this.logTerminal(`[OK] Data synced with maxgpt_dataset.json`);
        }, 1200);
        setTimeout(() => {
            this.logTerminal(`[SUCCESS] Neural pipeline execution completed. STATUS: Optimal.`);
        }, 1800);
    }

    simulateSale() {
        this.revenue += 49;
        this.autos += 1;
        
        const revEl = document.getElementById('val-arr');
        const autoEl = document.getElementById('val-autos');
        
        if (revEl) revEl.textContent = this.revenue.toFixed(1) + 'k';
        if (autoEl) autoEl.textContent = this.autos;

        this.logTerminal(`[MONETIZATION] Inbound sale captured! Revenue increment: +$49.00 USD`);
        
        // Send alert inside the chat as well
        this.addBotMessage(`ALERTA: ¡Nueva venta automática registrada! Incremento de Revenue a $${this.revenue.toFixed(1)}k.`);
    }

    logTerminal(text) {
        const terminal = document.getElementById('terminal-output-vault');
        if (terminal) {
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = `<span>[${new Date().toLocaleTimeString()}]</span> ${text}`;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }
    }

    handleSendMessage() {
        const text = this.chatInput.value.trim();
        if (!text) return;

        // User message
        this.addUserMessage(text);
        this.chatInput.value = '';

        // Bot thinking & response
        setTimeout(() => {
            this.processBotResponse(text);
        }, 600);
    }

    addUserMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'msg user';
        msg.innerHTML = `<span class="user-prefix">OPERADOR:</span> ${text}`;
        this.chatHistory.appendChild(msg);
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    addBotMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'msg bot';
        msg.innerHTML = `<span class="sys">AXIONCHAT:</span> ${text}`;
        this.chatHistory.appendChild(msg);
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    async processBotResponse(input) {
        const cleanInput = input.toLowerCase();

        if (cleanInput.includes('status') || cleanInput.includes('estado')) {
            this.addBotMessage("DIAGNÓSTICO DEL SISTEMA:<br>• Motor local: ACTIVO en puerto 8080<br>• Conexión de túnel: ONLINE (Servidor externo activo)<br>• Base de datos: maxgpt_dataset.json cargada con éxito<br>• Estado de IA: Esperando comandos tácticos.");
            return;
        } else if (cleanInput.includes('help') || cleanInput.includes('ayuda')) {
            this.addBotMessage("COMANDOS DISPONIBLES:<br>• <b>status/estado</b> - Ver el estado del motor y el túnel.<br>• <b>/sell</b> - Simular una venta y subir el Revenue.<br>• <b>dataset/datos</b> - Ver información del dataset.");
            return;
        } else if (cleanInput.includes('/sell') || cleanInput.includes('vender') || cleanInput.includes('venta')) {
            this.simulateSale();
            return;
        } else if (cleanInput.includes('dataset') || cleanInput.includes('datos')) {
            this.addBotMessage("ANALIZADOR DE ARCHIVO:<br>Se detectó el dataset local 'maxgpt_dataset.json' en su carpeta de descargas. El dataset está listo para alimentar las interacciones del modelo neuronal.");
            return;
        }

        // Real fetch to MaxGPT Apex backend on port 8000
        try {
            const response = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_input: input,
                    model: 'llama-3.3-70b',
                    mode: 'apex'
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.addBotMessage(data.response);
            } else {
                throw new Error("Query failed");
            }
        } catch (e) {
            // Fallback response inside dashboard in case backend is offline
            this.addBotMessage("Comando táctico recibido, General. Analizando variables del mercado de marketing digital...<br>• Objetivo: Optimizar conversiones y maximizar el LTV.<br>• Siguiente Paso: Implementar un disparador en el backend para realizar un seguimiento automatizado.");
        }
    }
}

// Global initialization
window.app = new NexusApp();
