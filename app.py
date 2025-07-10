import streamlit as st
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import tempfile
import os
import io
import json

# Configuração da página
st.set_page_config(
    page_title="Sistema de Recorte PDF",
    page_icon="✂️",
    layout="wide"
)

def pdf_to_image(pdf_path, page_num=0, dpi=200):
    """Converte uma página específica do PDF para imagem"""
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        
        # Converte para imagem com DPI especificado
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Converte para PIL Image
        img = Image.open(io.BytesIO(img_data))
        doc.close()
        
        return img
    except Exception as e:
        st.error(f"Erro ao converter PDF para imagem: {str(e)}")
        return None

def crop_image(image, x1, y1, x2, y2):
    """Recorta a imagem nas coordenadas especificadas"""
    try:
        # Garante que as coordenadas estão dentro dos limites da imagem
        width, height = image.size
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        # Recorta a imagem
        cropped = image.crop((x1, y1, x2, y2))
        return cropped
    except Exception as e:
        st.error(f"Erro ao recortar imagem: {str(e)}")
        return None

def draw_rectangle_on_image(image, x1, y1, x2, y2):
    """Desenha um retângulo na imagem para visualizar a área de recorte"""
    try:
        # Converte para numpy array
        img_array = np.array(image)
        
        # Desenha o retângulo (contorno vermelho)
        import cv2
        cv2.rectangle(img_array, (x1, y1), (x2, y2), (255, 0, 0), 3)
        
        # Converte de volta para PIL Image
        return Image.fromarray(img_array)
    except Exception as e:
        st.error(f"Erro ao desenhar retângulo: {str(e)}")
        return image

def main():
    st.title("✂️ Sistema de Recorte PDF")
    st.markdown("### Ferramenta para definir coordenadas de recorte em PDFs")
    
    # Sidebar para configurações
    st.sidebar.header("⚙️ Configurações")
    
    # Upload do arquivo PDF
    uploaded_file = st.sidebar.file_uploader(
        "Carregue seu arquivo PDF",
        type=['pdf'],
        help="Selecione o arquivo PDF para recorte"
    )
    
    if uploaded_file is not None:
        # Salva o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = tmp_file.name
        
        try:
            # Abre o PDF para obter informações
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            st.sidebar.success(f"PDF carregado: {total_pages} páginas")
            
            # Seleção da página
            page_num = st.sidebar.selectbox(
                "Selecione a página",
                range(total_pages),
                format_func=lambda x: f"Página {x + 1}"
            )
            
            # Configurações de DPI
            dpi = st.sidebar.slider("DPI da imagem", 100, 300, 200, 10)
            
            # Converte a página selecionada para imagem
            with st.spinner("Convertendo PDF para imagem..."):
                page_image = pdf_to_image(pdf_path, page_num, dpi)
            
            if page_image:
                width, height = page_image.size
                
                # Layout em duas colunas
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("📄 Página Original")
                    st.image(page_image, caption=f"Página {page_num + 1}", use_column_width=True)
                    st.info(f"Dimensões: {width} x {height} pixels")
                
                with col2:
                    st.subheader("✂️ Definir Coordenadas")
                    
                    # Coordenadas de recorte
                    st.markdown("**Coordenadas do recorte:**")
                    
                    # Usando slider para melhor controle
                    x1 = st.slider("X1 (esquerda)", 0, width, 0, key="x1")
                    y1 = st.slider("Y1 (topo)", 0, height, 0, key="y1")
                    x2 = st.slider("X2 (direita)", 0, width, width//2, key="x2")
                    y2 = st.slider("Y2 (fundo)", 0, height, height//2, key="y2")
                    
                    # Mostra as coordenadas atuais
                    st.code(f"Coordenadas: ({x1}, {y1}) -> ({x2}, {y2})")
                    
                    # Calcula dimensões do recorte
                    crop_width = x2 - x1
                    crop_height = y2 - y1
                    st.info(f"Tamanho do recorte: {crop_width} x {crop_height} pixels")
                
                # Seção de visualização do recorte
                if x2 > x1 and y2 > y1:
                    st.subheader("🎯 Visualização do Recorte")
                    
                    col3, col4 = st.columns([1, 1])
                    
                    with col3:
                        st.markdown("**Área marcada na página:**")
                        # Desenha retângulo na imagem original
                        marked_image = draw_rectangle_on_image(page_image, x1, y1, x2, y2)
                        st.image(marked_image, caption="Área de recorte em vermelho", use_column_width=True)
                    
                    with col4:
                        st.markdown("**Região recortada:**")
                        # Mostra apenas a região recortada
                        cropped_image = crop_image(page_image, x1, y1, x2, y2)
                        if cropped_image:
                            st.image(cropped_image, caption=f"Recorte: {crop_width}x{crop_height}", use_column_width=True)
                else:
                    st.warning("⚠️ Coordenadas inválidas. X2 deve ser maior que X1 e Y2 deve ser maior que Y1.")
                
                # Seção de presets
                st.subheader("⚡ Presets Rápidos")
                preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
                
                with preset_col1:
                    if st.button("📄 Página Inteira"):
                        st.session_state.x1 = 0
                        st.session_state.y1 = 0
                        st.session_state.x2 = width
                        st.session_state.y2 = height
                        st.rerun()
                
                with preset_col2:
                    if st.button("📊 Centro"):
                        st.session_state.x1 = width // 4
                        st.session_state.y1 = height // 4
                        st.session_state.x2 = 3 * width // 4
                        st.session_state.y2 = 3 * height // 4
                        st.rerun()
                
                with preset_col3:
                    if st.button("📋 Metade Superior"):
                        st.session_state.x1 = 0
                        st.session_state.y1 = 0
                        st.session_state.x2 = width
                        st.session_state.y2 = height // 2
                        st.rerun()
                
                with preset_col4:
                    if st.button("📋 Metade Inferior"):
                        st.session_state.x1 = 0
                        st.session_state.y1 = height // 2
                        st.session_state.x2 = width
                        st.session_state.y2 = height
                        st.rerun()
                
                # Exportação das coordenadas
                st.subheader("💾 Exportar Configuração")
                
                distribuidora_name = st.text_input("Nome da distribuidora (opcional):", "")
                
                config_dict = {
                    "distribuidora": distribuidora_name,
                    "arquivo": uploaded_file.name,
                    "pagina": page_num + 1,
                    "coordenadas": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2
                    },
                    "dimensoes_originais": {
                        "width": width,
                        "height": height
                    },
                    "dimensoes_recorte": {
                        "width": crop_width,
                        "height": crop_height
                    },
                    "dpi": dpi
                }
                
                # Mostra o JSON da configuração
                st.code(json.dumps(config_dict, indent=2, ensure_ascii=False), language='json')
                
                # Botão de download
                config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Download Configuração JSON",
                    data=config_json,
                    file_name=f"recorte_{distribuidora_name or 'config'}_{page_num+1}.json",
                    mime="application/json"
                )
        
        finally:
            # Remove o arquivo temporário
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    else:
        st.info("👆 Carregue um arquivo PDF para começar a definir coordenadas de recorte.")
        
        # Instruções de uso
        st.markdown("""
        ### 📋 Como usar:
        
        1. **Upload**: Carregue seu arquivo PDF
        2. **Página**: Selecione a página desejada
        3. **Coordenadas**: Use os sliders para definir a área de recorte
        4. **Visualização**: Veja a área marcada e o recorte final
        5. **Presets**: Use os botões rápidos para configurações comuns
        6. **Exportar**: Salve a configuração em JSON
        
        ### 🎯 Dicas:
        
        - **X1, Y1**: Canto superior esquerdo do recorte
        - **X2, Y2**: Canto inferior direito do recorte
        - Use **DPI mais alto** para melhor precisão
        - **Presets** ajudam a começar rapidamente
        - O **JSON exportado** pode ser usado em sistemas automatizados
        """)

if __name__ == "__main__":
    main()
