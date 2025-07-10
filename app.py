import streamlit as st
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
from paddleocr import PaddleOCR
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Sistema de Teste de Recorte PDF",
    page_icon="📄",
    layout="wide"
)

# Inicialização do PaddleOCR
@st.cache_resource
def init_ocr():
    """Inicializa o PaddleOCR com cache para otimização"""
    return PaddleOCR(use_angle_cls=True, lang='pt')

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

def extract_text_from_image(image, ocr_engine):
    """Extrai texto da imagem usando PaddleOCR"""
    try:
        # Converte PIL Image para numpy array
        img_array = np.array(image)
        
        # Aplica OCR
        result = ocr_engine.ocr(img_array, cls=True)
        
        # Processa os resultados
        extracted_text = []
        confidence_scores = []
        
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                extracted_text.append(text)
                confidence_scores.append(confidence)
        
        return extracted_text, confidence_scores
    except Exception as e:
        st.error(f"Erro na extração de texto: {str(e)}")
        return [], []

def main():
    st.title("🔍 Sistema de Teste de Recorte PDF")
    st.markdown("### Ferramenta para testar coordenadas de recorte em faturas de energia")
    
    # Sidebar para configurações
    st.sidebar.header("⚙️ Configurações")
    
    # Upload do arquivo PDF
    uploaded_file = st.sidebar.file_uploader(
        "Carregue seu arquivo PDF",
        type=['pdf'],
        help="Selecione o arquivo PDF da fatura para análise"
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
            
            st.sidebar.success(f"PDF carregado com sucesso! ({total_pages} páginas)")
            
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
                import io
                page_image = pdf_to_image(pdf_path, page_num, dpi)
            
            if page_image:
                # Layout em duas colunas
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("📄 Página Original")
                    st.image(page_image, caption=f"Página {page_num + 1}", use_column_width=True)
                    
                    # Mostra as dimensões da imagem
                    width, height = page_image.size
                    st.info(f"Dimensões: {width} x {height} pixels")
                
                with col2:
                    st.subheader("✂️ Configuração de Recorte")
                    
                    # Coordenadas de recorte
                    st.markdown("**Coordenadas do recorte (X1, Y1, X2, Y2):**")
                    
                    col2a, col2b = st.columns(2)
                    with col2a:
                        x1 = st.number_input("X1 (esquerda)", min_value=0, max_value=width, value=0)
                        y1 = st.number_input("Y1 (topo)", min_value=0, max_value=height, value=0)
                    
                    with col2b:
                        x2 = st.number_input("X2 (direita)", min_value=0, max_value=width, value=width//2)
                        y2 = st.number_input("Y2 (fundo)", min_value=0, max_value=height, value=height//2)
                    
                    # Botão para aplicar recorte
                    if st.button("🔍 Aplicar Recorte", type="primary"):
                        if x2 > x1 and y2 > y1:
                            cropped_image = crop_image(page_image, x1, y1, x2, y2)
                            
                            if cropped_image:
                                st.subheader("📋 Resultado do Recorte")
                                st.image(cropped_image, caption=f"Recorte: ({x1}, {y1}) -> ({x2}, {y2})")
                                
                                # Extração de texto
                                with st.spinner("Extraindo texto com OCR..."):
                                    ocr_engine = init_ocr()
                                    extracted_text, confidence_scores = extract_text_from_image(cropped_image, ocr_engine)
                                
                                if extracted_text:
                                    st.subheader("📝 Texto Extraído")
                                    
                                    # Cria DataFrame com os resultados
                                    df_results = pd.DataFrame({
                                        'Texto': extracted_text,
                                        'Confiança': [f"{conf:.2%}" for conf in confidence_scores]
                                    })
                                    
                                    st.dataframe(df_results, use_container_width=True)
                                    
                                    # Mostra o texto completo
                                    full_text = "\n".join(extracted_text)
                                    st.text_area("Texto completo extraído:", full_text, height=200)
                                    
                                    # Estatísticas
                                    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
                                    st.metric("Confiança média do OCR", f"{avg_confidence:.2%}")
                                    
                                else:
                                    st.warning("Nenhum texto foi extraído da região recortada.")
                        else:
                            st.error("Coordenadas inválidas. X2 deve ser maior que X1 e Y2 deve ser maior que Y1.")
                
                # Seção de presets para distribuidoras
                st.subheader("⚡ Presets de Distribuidoras")
                st.markdown("Coordenadas pré-definidas para facilitar o teste:")
                
                preset_col1, preset_col2, preset_col3 = st.columns(3)
                
                with preset_col1:
                    if st.button("📍 CEMIG - Tabela"):
                        st.session_state.preset_coords = (100, 400, 500, 800)
                        st.rerun()
                
                with preset_col2:
                    if st.button("📍 ENEL - Tabela"):
                        st.session_state.preset_coords = (80, 350, 520, 750)
                        st.rerun()
                
                with preset_col3:
                    if st.button("📍 COPEL - Tabela"):
                        st.session_state.preset_coords = (90, 380, 510, 780)
                        st.rerun()
                
                # Aplica preset se selecionado
                if hasattr(st.session_state, 'preset_coords'):
                    px1, py1, px2, py2 = st.session_state.preset_coords
                    st.info(f"Preset aplicado: ({px1}, {py1}) -> ({px2}, {py2})")
                    delattr(st.session_state, 'preset_coords')
                
                # Seção de exportação das coordenadas
                st.subheader("💾 Exportar Configuração")
                
                config_dict = {
                    'distribuidora': st.text_input("Nome da distribuidora:", ""),
                    'pagina': page_num,
                    'coordenadas': {
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2
                    },
                    'dpi': dpi
                }
                
                if st.button("📥 Exportar JSON"):
                    import json
                    config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Download configuração",
                        data=config_json,
                        file_name=f"config_{config_dict['distribuidora'] or 'distribuidora'}.json",
                        mime="application/json"
                    )
                
                st.code(json.dumps(config_dict, indent=2, ensure_ascii=False), language='json')
        
        finally:
            # Remove o arquivo temporário
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    else:
        st.info("👆 Carregue um arquivo PDF para começar a testar os recortes.")
        
        # Instruções de uso
        st.markdown("""
        ### 📋 Como usar:
        
        1. **Upload**: Carregue seu arquivo PDF de fatura
        2. **Página**: Selecione a página que contém a tabela de dados
        3. **Coordenadas**: Defina as coordenadas X1, Y1 (canto superior esquerdo) e X2, Y2 (canto inferior direito)
        4. **Recorte**: Clique em "Aplicar Recorte" para visualizar a área selecionada
        5. **OCR**: O sistema extrairá automaticamente o texto da região recortada
        6. **Exportar**: Salve a configuração em JSON para uso posterior
        
        ### 🎯 Dicas:
        - Use DPI mais alto (200-300) para melhor qualidade de OCR
        - Teste diferentes coordenadas para encontrar a região ideal
        - Os presets são pontos de partida - ajuste conforme necessário
        - Verifique a confiança do OCR para validar a qualidade da extração
        """)

if __name__ == "__main__":
    main()
