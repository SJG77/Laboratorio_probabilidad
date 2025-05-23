import os
import io
import base64
from flask import Flask, render_template_string, request, flash
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from scipy.stats import norm


app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'una_clave_secreta_de_desarrollo_temporal_no_usar_en_produccion')



HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis y Comparación de Curvas Normales</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #e9eff1;
            color: #333;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .main-container {
            background-color: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            width: 90%;
            max-width: 900px;
            margin-bottom: 30px;
            box-sizing: border-box;
        }
        h1, h2 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 25px;
            font-weight: 600;
        }
        .form-section {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        label {
            font-weight: bold;
            margin-bottom: 8px;
            color: #555;
            font-size: 0.95em;
        }
        input[type="file"],
        input[type="text"] {
            padding: 12px;
            border: 1px solid #dcdcdc;
            border-radius: 8px;
            font-size: 1em;
            box-sizing: border-box;
            width: 100%;
            transition: border-color 0.3s ease;
        }
        input[type="file"]:focus,
        input[type="text"]:focus {
            border-color: #007bff;
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
        }
        .submit-btn {
            background-color: #007bff;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            cursor: pointer;
            transition: background-color 0.3s ease, transform 0.2s ease;
            margin-top: 20px;
            width: auto; /* Allow button to size naturally */
            align-self: center; /* Center the button in grid */
        }
        .submit-btn:hover {
            background-color: #0056b3;
            transform: translateY(-2px);
        }
        .plot-display {
            text-align: center;
            margin-top: 30px;
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #eee;
        }
        .plot-display img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        .message-container {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-size: 1em;
            margin-bottom: 20px;
        }
        .message-container.error {
            background-color: #ffe0e0;
            color: #cc0000;
            border: 1px solid #ff9999;
        }
        .message-container.info {
            background-color: #e0f0ff;
            color: #0066cc;
            border: 1px solid #99ccff;
        }
        .sub-header {
            text-align: center;
            color: #4a6a82;
            font-size: 1.3em;
            margin-top: 30px;
            margin-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
        }
        @media (min-width: 768px) {
            .form-section {
                grid-template-columns: 1fr 1fr;
            }
            .submit-btn {
                grid-column: span 2; /* Make button span both columns */
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <h1>Análisis y Comparación de Curvas Normales</h1>
        <div class="message-container info">
            Sube un archivo Excel (.xlsx, .xls) con tus datos.
            Introduce el nombre de la columna numérica a analizar y los parámetros para una curva de referencia.
        </div>

        {# Mensajes flash #}
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="message-container {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form action="/" method="post" enctype="multipart/form-data">
            <div class="form-section">
                <div class="form-group">
                    <label for="excel_file">Archivo Excel:</label>
                    <input type="file" name="excel_file" id="excel_file" accept=".xlsx, .xls" required>
                </div>
                <div class="form-group">
                    <label for="column_name">Nombre de la Columna a Analizar:</label>
                    <input type="text" name="column_name" id="column_name" placeholder="Ej. 'Valor', 'Edad'" required>
                </div>
            </div>

            <h2 class="sub-header">Parámetros de la Curva de Referencia</h2>
            <div class="form-section">
                <div class="form-group">
                    <label for="ref_mean">Media (μ):</label>
                    <input type="text" name="ref_mean" id="ref_mean" placeholder="Ej. 0" value="{{ ref_mean }}" required>
                </div>
                <div class="form-group">
                    <label for="ref_std_dev">Desviación Estándar (σ):</label>
                    <input type="text" name="ref_std_dev" id="ref_std_dev" placeholder="Ej. 1" value="{{ ref_std_dev }}" required>
                </div>
                <button type="submit" class="submit-btn">Generar Curvas</button>
            </div>
        </form>

        {% if plot_url %}
            <div class="plot-display">
                <img src="{{ plot_url }}" alt="Gráfico de Comparación de Curvas Normales">
            </div>
        {% endif %}
    </div>
</body>
</html>
"""


def generate_normal_comparison_plot(data_series, ref_mean, ref_std_dev, column_name):
    """
    Genera un gráfico de comparación de curvas normales.
    Devuelve la imagen del gráfico codificada en base64.
    """
    
    mu_data = np.mean(data_series)
    sigma_data = np.std(data_series)

    
    min_val = min(data_series.min(), ref_mean - 3 * ref_std_dev, mu_data - 3 * sigma_data)
    max_val = max(data_series.max(), ref_mean + 3 * ref_std_dev, mu_data + 3 * sigma_data)
    x = np.linspace(min_val - 0.1 * (max_val - min_val), max_val + 0.1 * (max_val - min_val), 500)


    p_data = norm.pdf(x, mu_data, sigma_data)
    p_ref = norm.pdf(x, ref_mean, ref_std_dev)

   
    plt.figure(figsize=(12, 7)) 
    
    
    plt.hist(data_series, bins=30, density=True, alpha=0.6, color='#6495ED', label='Histograma de Datos') 

   
    plt.plot(x, p_data, 'k', linewidth=2.5, label=f'Curva Normal (Datos): $\\mu$={mu_data:.2f}, $\\sigma$={sigma_data:.2f}')

    
    plt.plot(x, p_ref, 'r--', linewidth=2.5, label=f'Curva de Referencia: $\\mu$={ref_mean:.2f}, $\\sigma$={ref_std_dev:.2f}')
    plt.title(f'Comparación de Curvas Normales para: {column_name}', fontsize=16)
    plt.xlabel(column_name, fontsize=12)
    plt.ylabel('Densidad de Probabilidad', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout() 

   
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0) 
    plt.close() 

  
    plot_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{plot_base64}"


@app.route('/', methods=['GET', 'POST'])
def dashboard():
    plot_url = None
    
    default_ref_mean = "0"
    default_ref_std_dev = "1"

    if request.method == 'POST':
       
        if 'excel_file' not in request.files:
            flash("No se adjuntó ningún archivo. Por favor, selecciona un archivo Excel.", "error")
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=default_ref_mean, ref_std_dev=default_ref_std_dev)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash("No se seleccionó ningún archivo. Por favor, selecciona un archivo Excel.", "error")
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=default_ref_mean, ref_std_dev=default_ref_std_dev)
        
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            flash("Formato de archivo no soportado. Por favor, sube un archivo .xlsx o .xls.", "error")
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=default_ref_mean, ref_std_dev=default_ref_std_dev)

        
        column_name = request.form.get('column_name', '').strip()
        if not column_name:
            flash("Por favor, introduce el nombre de la columna a analizar.", "error")
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=default_ref_mean, ref_std_dev=default_ref_std_dev)

    
        try:
            ref_mean_str = request.form.get('ref_mean', default_ref_mean).strip()
            ref_std_dev_str = request.form.get('ref_std_dev', default_ref_std_dev).strip()

            ref_mean = float(ref_mean_str)
            ref_std_dev = float(ref_std_dev_str)

            if ref_std_dev <= 0:
                flash("La desviación estándar de referencia debe ser un número positivo mayor que cero.", "error")
                return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                              ref_mean=ref_mean_str, ref_std_dev=ref_std_dev_str)
        except ValueError:
            flash("La media y desviación estándar de referencia deben ser números válidos.", "error")
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=ref_mean_str, ref_std_dev=ref_std_dev_str)

    
        try:
            df = pd.read_excel(file)

            if column_name not in df.columns:
                flash(f"La columna '{column_name}' no se encuentra en el archivo Excel.", "error")
                return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                              ref_mean=ref_mean_str, ref_std_dev=ref_std_dev_str)
            
          
            data_series = pd.to_numeric(df[column_name], errors='coerce').dropna()

            if data_series.empty:
                flash(f"La columna '{column_name}' no contiene datos numéricos válidos para analizar.", "error")
                return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                              ref_mean=ref_mean_str, ref_std_dev=ref_std_dev_str)

          
            plot_url = generate_normal_comparison_plot(data_series, ref_mean, ref_std_dev, column_name)
            
           
            default_ref_mean = ref_mean_str
            default_ref_std_dev = ref_std_dev_str

        except Exception as e:
            flash(f"Ocurrió un error al procesar el archivo o generar el gráfico: {e}", "error")
            
            return render_template_string(HTML_TEMPLATE, plot_url=None, 
                                          ref_mean=ref_mean_str, ref_std_dev=ref_std_dev_str)

   
    return render_template_string(HTML_TEMPLATE, plot_url=plot_url, 
                                  ref_mean=default_ref_mean, ref_std_dev=default_ref_std_dev)


if __name__ == '__main__':
    app.run(debug=True)