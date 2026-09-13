
import math
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def calcular_tempo_voo(v0, theta, y0, g):
    vy = v0 * math.sin(theta)
    return (vy + math.sqrt(vy ** 2 + 2 * g * y0)) / g


def calcular_altura_maxima(v0, theta, y0, g):
    vy = v0 * math.sin(theta)
    return y0 + (vy ** 2) / (2 * g)


def calcular_alcance(v0, theta, tempo_voo, x0=0.0):
    return x0 + v0 * math.cos(theta) * tempo_voo


def calcular_trajetoria(v0, theta, y0, g, x0=0.0, n_pontos=300):
    tempo_voo = calcular_tempo_voo(v0, theta, y0, g)

    xs, ys = [], []
    for i in range(n_pontos + 1):
        t = tempo_voo * i / n_pontos
        x = x0 + v0 * math.cos(theta) * t                     
        y = y0 + v0 * math.sin(theta) * t - 0.5 * g * t ** 2   
        xs.append(x)
        ys.append(max(y, 0.0)) 
    return xs, ys


def validar_parametros(v0, theta_deg, y0, g):
    if v0 <= 0:
        return False, "A velocidade inicial deve ser maior que zero."
    if not (0 < theta_deg < 90):
        return False, "O ângulo deve estar entre 0° e 90° (exclusive)."
    if y0 < 0:
        return False, "A altura inicial não pode ser negativa."
    if g <= 0:
        return False, "A gravidade deve ser maior que zero."
    return True, ""

class SimuladorProjetil:

    def __init__(self, master):
        self.master = master
        master.title("Lançamento de Projéteis — Simulação Interativa")
        master.geometry("1150x680")
        master.configure(bg="#EAF2FB")

        self.manter_trajetorias = tk.BooleanVar(value=False)
        self.animando = False
        self._ultima_trajetoria = None
        self._marcador = None
        self._entradas = {}
        self._trajetorias_lancadas = []

        self._montar_layout()
        self.atualizar_grafico()

    def _montar_layout(self):
        painel_controles = tk.Frame(self.master, bg="#EAF2FB", padx=15, pady=15)
        painel_controles.pack(side="left", fill="y")

        painel_grafico = tk.Frame(self.master, bg="white")
        painel_grafico.pack(side="right", fill="both", expand=True)

        tk.Label(painel_controles, text="Parâmetros do Lançamento",
                 font=("Arial", 14, "bold"), bg="#EAF2FB").pack(pady=(0, 15))

        self.v0_var = tk.DoubleVar(value=50)
        self._criar_slider(painel_controles, "v0", "Velocidade inicial v0 (m/s)",
                            self.v0_var, 5, 150)

        self.theta_var = tk.DoubleVar(value=45)
        self._criar_slider(painel_controles, "theta", "Ângulo de lançamento θ (°)",
                            self.theta_var, 1, 89)

        self.y0_var = tk.DoubleVar(value=0)
        self._criar_slider(painel_controles, "y0", "Altura inicial y0 (m)",
                            self.y0_var, 0, 50)

        self.g_var = tk.DoubleVar(value=9.8)
        self._criar_slider(painel_controles, "g", "Gravidade g (m/s²)",
                            self.g_var, 1.6, 24.8, resolution=0.1)

        tk.Checkbutton(painel_controles,
                        text="Manter lançamentos anteriores na tela",
                        variable=self.manter_trajetorias,
                        bg="#EAF2FB").pack(anchor="w", pady=(5, 15))

        self.btn_lancar = tk.Button(painel_controles, text="🚀  Lançar",
                                     font=("Arial", 12, "bold"),
                                     bg="#1976D2", fg="white",
                                     activebackground="#1565C0",
                                     command=self.lancar)
        self.btn_lancar.pack(fill="x", pady=(0, 15))

        resultado_frame = tk.LabelFrame(painel_controles, text="Resultados",
                                         bg="#EAF2FB", font=("Arial", 11, "bold"))
        resultado_frame.pack(fill="x", pady=(5, 10))

        self.lbl_alcance = tk.Label(resultado_frame, text="Alcance (R): -- m",
                                     bg="#EAF2FB", anchor="w")
        self.lbl_alcance.pack(fill="x", padx=5, pady=2)

        self.lbl_altura = tk.Label(resultado_frame, text="Altura máxima (y_max): -- m",
                                    bg="#EAF2FB", anchor="w")
        self.lbl_altura.pack(fill="x", padx=5, pady=2)

        self.lbl_tempo = tk.Label(resultado_frame, text="Tempo de voo (t_voo): -- s",
                                   bg="#EAF2FB", anchor="w")
        self.lbl_tempo.pack(fill="x", padx=5, pady=2)

        self.lbl_status = tk.Label(painel_controles, text="", fg="#B00020",
                                    bg="#EAF2FB", wraplength=230, justify="left")
        self.lbl_status.pack(fill="x", pady=(5, 0))

        self.fig = Figure(figsize=(7, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=painel_grafico)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _criar_slider(self, parent, chave, texto, variavel, minimo, maximo, resolution=1):
        tk.Label(parent, text=texto, bg="#EAF2FB").pack(anchor="w")

        linha = tk.Frame(parent, bg="#EAF2FB")
        linha.pack(fill="x", pady=(0, 8))

        escala = tk.Scale(linha, variable=variavel, from_=minimo, to=maximo,
                           orient="horizontal", resolution=resolution,
                           bg="#EAF2FB", highlightthickness=0, length=175,
                           command=lambda _valor: self._ao_mover_slider(chave))
        escala.pack(side="left")

        entrada = tk.Entry(linha, width=6)
        entrada.insert(0, str(variavel.get()))
        entrada.pack(side="left", padx=(5, 0))
        self._entradas[chave] = entrada

        def _ao_confirmar_entrada(_evt=None):
            texto_digitado = entrada.get().strip().replace(",", ".")
            try:
                valor = float(texto_digitado)
            except ValueError:
                self.lbl_status.config(
                    text=f"⚠ Digite um número válido para '{texto}'.")
                entrada.delete(0, tk.END)
                entrada.insert(0, str(variavel.get()))
                return

            if not (minimo <= valor <= maximo):
                self.lbl_status.config(
                    text=f"⚠ '{texto}' deve estar entre {minimo} e {maximo}.")
                entrada.delete(0, tk.END)
                entrada.insert(0, str(variavel.get()))
                return

            self.lbl_status.config(text="")
            variavel.set(valor)
            self.atualizar_grafico()

        entrada.bind("<Return>", _ao_confirmar_entrada)
        entrada.bind("<FocusOut>", _ao_confirmar_entrada)

    def _ao_mover_slider(self, chave):
        variavel = {"v0": self.v0_var, "theta": self.theta_var,
                    "y0": self.y0_var, "g": self.g_var}[chave]
        entrada = self._entradas[chave]
        entrada.delete(0, tk.END)
        entrada.insert(0, str(variavel.get()))
        self.atualizar_grafico()

    def atualizar_grafico(self):
        v0 = self.v0_var.get()
        theta_deg = self.theta_var.get()  
        y0 = self.y0_var.get()
        g = self.g_var.get()
        valido, mensagem = validar_parametros(v0, theta_deg, y0, g)
        if not valido:
            self.lbl_status.config(text="⚠ " + mensagem)
            return
        self.lbl_status.config(text="")

        theta = math.radians(theta_deg)
        x0 = 0.0

        tempo_voo = calcular_tempo_voo(v0, theta, y0, g)
        altura_max = calcular_altura_maxima(v0, theta, y0, g)
        alcance = calcular_alcance(v0, theta, tempo_voo, x0)
        xs, ys = calcular_trajetoria(v0, theta, y0, g, x0)
        self._ultima_trajetoria = (xs, ys)

        self.lbl_alcance.config(text=f"Alcance (R): {alcance:.2f} m")
        self.lbl_altura.config(text=f"Altura máxima (y_max): {altura_max:.2f} m")
        self.lbl_tempo.config(text=f"Tempo de voo (t_voo): {tempo_voo:.2f} s")
        self._redesenhar_grafico(xs, ys)

    def _redesenhar_grafico(self, xs_preview=None, ys_preview=None):
        self.ax.clear()

        for xs_l, ys_l in self._trajetorias_lancadas:
            self.ax.plot(xs_l, ys_l, color="#1976D2", linewidth=2)

        if xs_preview is not None:
            self.ax.plot(xs_preview, ys_preview, color="#90A4AE",
                          linewidth=1.5, linestyle="--")

        self.ax.set_xlabel("Distância horizontal x (m)")
        self.ax.set_ylabel("Altura y (m)")
        self.ax.set_title("Trajetória do Projétil")
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.set_xlim(left=0)
        self.ax.set_ylim(bottom=0)
        self.ax.set_aspect("equal", adjustable="datalim")

        self.canvas.draw_idle()

    def lancar(self):
        if self.animando or self._ultima_trajetoria is None:
            return

        xs, ys = self._ultima_trajetoria
        if not self.manter_trajetorias.get():
            self._trajetorias_lancadas.clear()
        self._trajetorias_lancadas.append((xs, ys))
        self._redesenhar_grafico()

        self._pontos_animacao = list(zip(xs, ys))
        self._indice_animacao = 0
        self.animando = True

        self._marcador, = self.ax.plot([xs[0]], [ys[0]], "o",
                                        color="#D32F2F", markersize=10, zorder=5)
        self._passo_animacao()

    def _passo_animacao(self):
        if self._indice_animacao >= len(self._pontos_animacao):
            self.animando = False
            return

        x, y = self._pontos_animacao[self._indice_animacao]
        self._marcador.set_data([x], [y])
        self.canvas.draw_idle()

        self._indice_animacao += 3
        self.master.after(20, self._passo_animacao)


if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorProjetil(root)
    root.mainloop()