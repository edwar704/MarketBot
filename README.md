# MarketBot — Dashboard inicial

Este proyecto es una maqueta de dashboard de señales de trading creada con Streamlit.

## Importante
- Los precios, señales, métricas y resultados son ficticios.
- No se conecta a Binance, OANDA ni ningún broker.
- No envía órdenes ni opera con dinero real.
- No utilices los datos de demostración para tomar decisiones financieras.

## Ejecutar en tu ordenador

1. Instala Python si aún no lo tienes.
2. Abre una terminal en esta carpeta.
3. Instala las dependencias:

   `pip install -r requirements.txt`

4. Inicia la aplicación:

   `streamlit run app.py`

Se abrirá una pestaña en tu navegador.

## Publicar en Streamlit Community Cloud

1. Sube `app.py` y `requirements.txt` a un repositorio de GitHub.
2. Entra en https://share.streamlit.io/
3. Elige el repositorio y selecciona `app.py` como archivo principal.
4. Pulsa Deploy.

No pongas claves API en el código. Cuando llegue el momento de conectar un proveedor, usaremos `st.secrets` y permisos mínimos, sin retiros habilitados.
