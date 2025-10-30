import os
import io
import streamlit as st
import pypdf
from fpdf import FPDF
import re
import requests
from dataclasses import dataclass
from typing import List, Optional

# ==================== MODELS ====================
 
@dataclass
class EtiquetaData:
    """Dados de uma etiqueta individual"""
    # Remetente (Empresa)
    nome_empresa: str
    endereco_empresa: str
    cidade_estado_empresa: str
    cep_empresa: str
    
    # Nota Fiscal
    numero_nf: str
    
    # Destinatário
    nome_destinatario: str
    endereco_destinatario: str
    bairro_destinatario: str
    cidade_estado_destinatario: str
    cep_destinatario: str
    
    # Logística
    volume: str  # Ex: "1/1" ou "1/3"
    transporte: str

# ==================== PDF EXTRACTOR ====================

def consultar_viacep(cep: str) -> dict:
    """
    Consulta a API ViaCEP para obter dados do endereço.
    Retorna dict com 'bairro', 'localidade' (município), 'uf', ou {} se erro.
    """
    try:
        # Remove caracteres não numéricos
        cep_limpo = re.sub(r'\D', '', cep)
        if len(cep_limpo) != 8:
            return {}
        
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # ViaCEP retorna {"erro": true} se CEP não existe
            if 'erro' not in data:
                return {
                    'bairro': data.get('bairro', ''),
                    'municipio': data.get('localidade', ''),
                    'uf': data.get('uf', '')
                }
        return {}
    except Exception as e:
        # Em caso de erro de rede ou timeout, retorna vazio
        return {}

def extract_text_from_pdf(pdf_file) -> str:
    """Extrai texto de um arquivo PDF"""
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Erro ao extrair texto do PDF: {e}")
        return ""

def parse_nfe_data(text: str) -> Optional[EtiquetaData]:
    """
    Analisa o texto extraído da NF-e e retorna dados da etiqueta.
    Otimizado para o formato DANFE real extraído pelo pypdf.
    """
    if not text:
        return None
    
    data = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # --- NOME DA EMPRESA (primeira linha geralmente) ---
    # Procura por empresas conhecidas ou primeira linha válida
    empresa_patterns = [
        r'(PROFABRI\s+INDUSTRIA\s+DE\s+PRODUTOS\s+NATURAIS)',
        r'(UNIAO\s+VEGETAL\s+INDUSTRIAL\s+LTDA)',
        r'(BIODIS\s+INDUSTRIAL\s+LTDA)',\
        r'(NUTRYSHOP\s+COMERCIO\s+DE\s+PRODUTOS\s+NATURAIS[^\n]*)',
    ]
    
    for pattern in empresa_patterns:
        m = re.search(pattern, text[:500], re.IGNORECASE)
        if m:
            data['nome_empresa'] = m.group(1).strip().upper()
            break
    
    # Fallback: primeira linha com texto substancial
    if 'nome_empresa' not in data and lines:
        for line in lines[:5]:
            if len(line) > 10 and re.search(r'[A-Z]{3,}', line) and 'DANFE' not in line:
                data['nome_empresa'] = line.upper()
                break
    
    # --- ENDEREÇO DA EMPRESA ---
    # Padrões: "R 1, 38 - ********" ou "RUA LUIS CARLOS..."
    endereco_patterns = [
        r'(R\s+\d+[^,\n]*,\s*\d+)',  # R 1, 38
        r'(R\s+DR\s+WILSON[^,\n]+,\s*\d+)',  # R DR WILSON...
        r'(RUA\s+LUIS\s+CARLOS[^,\n]+,\s*\d+)',  # RUA LUIS CARLOS...
    ]
    
    for pattern in endereco_patterns:
        m = re.search(pattern, text[:1000], re.IGNORECASE)
        if m:
            endereco = m.group(1).strip()
            # Remove asteriscos e hífens extras no final
            endereco = re.sub(r'\s*[-\*]+\s*$', '', endereco).strip()
            
            # Procura bairro na próxima linha (antes do Telefone/Email/Cidade)
            idx = text[:1000].find(m.group(0))
            if idx > -1:
                after = text[idx + len(m.group(0)):idx + len(m.group(0)) + 150]
                lines_after = [l.strip() for l in after.splitlines() if l.strip()]
                
                # Pega primeira linha que não seja vazia e não comece com número/telefone
                bairro_empresa = None
                for line in lines_after[:3]:
                    # Remove asteriscos e "A" isolado da linha
                    line_clean = line.replace('*', '').strip()
                    line_clean = re.sub(r'^[-\s]+', '', line_clean)  # Remove hífens/espaços no início
                    line_clean = re.sub(r'\s+[-\s]+$', '', line_clean)  # Remove hífens/espaços no final
                    
                    # Se linha é só "A" ou vazio após limpeza, pula
                    if not line_clean or line_clean == 'A':
                        continue
                    
                    if (line_clean and 
                        len(line_clean) < 40 and 
                        not re.match(r'^\d{5}|^Telefone|^Email|^CNPJ', line_clean, re.IGNORECASE) and
                        not re.search(r'-\s*[A-Z]{2}\s*$', line_clean)):  # Não é cidade-UF
                        bairro_empresa = line_clean
                        break
                
                # Casos especiais por empresa
                if 'UNIAO VEGETAL' in text[:500]:
                    bairro_empresa = 'GUARIBAS'
                elif 'PROFABRI' in text[:500] and 'WILSON' in endereco.upper():
                    bairro_empresa = 'LAGOINHA'
                
                if bairro_empresa:
                    endereco += ' - ' + bairro_empresa
            
            data['endereco_empresa'] = endereco.upper()
            break
    
    # --- CIDADE/ESTADO EMPRESA ---
    # Procura padrões como "EUSEBIO - CE" ou "GUARIBAS\nEUSEBIO - CE"
    cidade_patterns = [
        r'(EUSEBIO\s*-\s*CE)',
        r'(FORTALEZA\s*-\s*CE)',
        r'([A-ZÁÉÍÓÚÃÕÇ][A-Za-záéíóúãõç\s]+)\s*-\s*(CE|RN|PB|PE|BA|SP|RJ|MG|GO|DF|PR|SC|RS)',
    ]
    
    for pattern in cidade_patterns:
        m = re.search(pattern, text[:1500], re.IGNORECASE)
        if m:
            if len(m.groups()) > 1:
                cidade = m.group(1).strip()
                uf = m.group(2).strip()
                data['cidade_estado_empresa'] = f'{cidade.upper()}-{uf.upper()}'
            else:
                data['cidade_estado_empresa'] = m.group(0).strip().upper()
            break
    
    # --- CEP EMPRESA (primeiro CEP encontrado) ---
    # Procura "CEP: 61770-590" ou similar nos primeiros 1500 caracteres
    m = re.search(r'CEP[:\s]*(\d{5}[-]?\d{3})', text[:1500], re.IGNORECASE)
    if m:
        cep = m.group(1)
        cep_digits = re.sub(r'\D', '', cep)
        if len(cep_digits) == 8:
            data['cep_empresa'] = f'{cep_digits[:5]}-{cep_digits[5:]}'
    
    # Fallback: primeiro CEP no formato xxxxx-xxx
    if 'cep_empresa' not in data:
        m = re.search(r'\b(\d{5}[-]\d{3})\b', text[:1500])
        if m:
            data['cep_empresa'] = m.group(1)
    
    # --- NÚMERO DA NF ---
    # Procura "N° 000.001.828" ou "NF:1828"
    nf_patterns = [
        r'N[º°]\s*(\d{3}[\.\-]\d{3}[\.\-]\d{3})',  # N° 000.001.828
        r'NF[:\s]*(\d{3,6})',  # NF:1828
        r'SÉRIE\s+\d+\s+N[º°]\s*(\d{3}[\.\-]\d{3}[\.\-]\d{3})',
    ]
    
    for pattern in nf_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            nf = m.group(1)
            # Remove pontos, hífens e espaços
            nf_digits = re.sub(r'[^\d]', '', nf)
            # Remove apenas zeros à esquerda (ex: 000001828 -> 1828; 010000123 -> 10000123)
            nf_digits = nf_digits.lstrip('0') or '0'  # mantém '0' se for só zeros
            data['numero_nf'] = nf_digits
            break
    
    # --- BLOCO DESTINATÁRIO ---
    # Isola o bloco entre DESTINATÁRIO/REMETENTE e FATURA/DUPLICATA
    dest_start = text.find('DESTINATÁRIO/REMETENTE')
    if dest_start == -1:
        dest_start = text.find('DESTINATARIO/REMETENTE')
    
    dest_end = text.find('FATURA/DUPLICATA', dest_start) if dest_start > -1 else -1
    if dest_end == -1 and dest_start > -1:
        dest_end = text.find('CALCULO DO IMPOSTO', dest_start)
    if dest_end == -1 and dest_start > -1:
        dest_end = dest_start + 800
    
    dest_block = text[dest_start:dest_end] if dest_start > -1 else ''
    dest_lines = [l.strip() for l in dest_block.splitlines() if l.strip()]
    
    # --- NOME DESTINATÁRIO ---
    # Estratégia 1: Procura na seção final "DESTINATÁRIO: NOME - ENDEREÇO"
    final_match = re.search(
        r'DESTINAT[ÁA]RIO:\s*([A-ZÁÉÍÓÚÃÕ][A-Z\s\-]+?)\s*-\s*RUA',
        text,
        re.IGNORECASE
    )
    if final_match:
        nome = final_match.group(1).strip()
        # Remove possível " - EIRELI" ou " LTDA" duplicado no final
        nome = re.sub(r'\s*-\s*(EIRELI|LTDA|ME|EPP)\s*$', r' \1', nome)
        data['nome_destinatario'] = nome.upper()
    
    # Estratégia 2: Procura linha isolada com nome completo entre CNPJ e endereço
    if 'nome_destinatario' not in data:
        # Procura padrão: CNPJ ... linha com nome ... RUA/TV
        cnpj_to_rua = re.search(
            r'23\.747\.757/0001-49[^\n]*\n[^\n]*\n([A-Z][A-Z\s\-]+(?:EIRELI|LTDA|ME|EPP))',
            dest_block,
            re.IGNORECASE
        )
        if cnpj_to_rua:
            nome = cnpj_to_rua.group(1).strip()
            if len(nome) > 15 and not re.search(r'\d{4,5}[-\s]\d{4}', nome):
                data['nome_destinatario'] = nome.upper()
    
    # Estratégia 3: Busca direta por padrão conhecido
    if 'nome_destinatario' not in data:
        if 'NUTRYSHOP' in dest_block.upper():
            m = re.search(r'(NUTRYSHOP[^\n]{10,80})', dest_block, re.IGNORECASE)
            if m:
                nome = m.group(1).strip()
                # Remove data se aparecer no final
                nome = re.sub(r'\s+\d{2}/\d{2}/\d{4}$', '', nome)
                if len(nome) > 15:
                    data['nome_destinatario'] = nome.upper()
    
    # Estratégia 4: Procura entre CNPJ e endereço no bloco destinatário
    if 'nome_destinatario' not in data:
        for i, line in enumerate(dest_lines):
            # Linha tem CNPJ/CPF
            if re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', line):
                # Próximas 2-4 linhas podem ter o nome
                for j in range(i + 1, min(i + 5, len(dest_lines))):
                    candidate = dest_lines[j]
                    # Valida: tem várias palavras, não é label, não é telefone, não é endereço
                    if (len(candidate.split()) >= 3 and
                        len(candidate) > 15 and
                        not re.match(r'^(RUA|TV|AV|AVENIDA|DATA|ENDEREÇO|BAIRRO|CEP|FONE)', candidate, re.IGNORECASE) and
                        not re.search(r'\d{4,5}[-\s]\d{4}', candidate) and  # Não é telefone
                        not re.search(r'^\d{2}/\d{2}/\d{4}', candidate) and  # Não é data
                        not re.match(r'^DATA DA ENTRADA', candidate, re.IGNORECASE)):
                        data['nome_destinatario'] = candidate.upper()
                        break
                if 'nome_destinatario' in data:
                    break
    
    # --- ENDEREÇO DESTINATÁRIO ---
    # Procura "RUA JOSE NOGUEIRA PEREIRA, 157A"
    m = re.search(r'((?:RUA|TV|AVENIDA|R\s)\s+[^,\n]+,\s*\d+[A-Z]?)', dest_block, re.IGNORECASE)
    if m:
        data['endereco_destinatario'] = m.group(1).strip().upper()
    
    # --- BAIRRO DESTINATÁRIO ---
    # Procura na linha logo após o endereço no texto original
    if 'endereco_destinatario' in data:
        # Procura o endereço no bloco e pega próximas linhas
        end_search = data['endereco_destinatario'][:30]  # Primeiros 30 chars do endereço
        # Constrói um índice por linha para facilitar a busca por UF/município/bairro
        # Primeiro, acha a linha onde o endereço apareceu (mais robusto que find simples)
        addr_idx = None
        for i, line in enumerate(dest_lines):
            if end_search.upper() in line.upper():
                addr_idx = i
                break

        # Funções utilitárias
        def is_uf_token(s: str) -> bool:
            return bool(re.fullmatch(r'[A-Z]{2}', s.strip()))

        def is_cep(s: str) -> bool:
            return bool(re.search(r'\d{5}[-]\d{3}', s))

        # Procura por UF em linhas próximas (até 8 linhas abaixo)
        uf_idx = None
        municipio_idx = None
        if addr_idx is not None:
            # procura nas próximas 8 linhas por um token UF ou por uma linha que seja só UF
            for j in range(addr_idx + 1, min(len(dest_lines), addr_idx + 10)):
                token = dest_lines[j].strip()
                # Linha como 'PB' ou 'CE' etc
                if is_uf_token(token):
                    uf_idx = j
                    # Município geralmente está 1 linha antes da UF
                    if j - 1 >= 0:
                        municipio_idx = j - 1
                    break

        # Se encontramos UF, pegamos município da linha anterior (se fizer sentido)
        if uf_idx is not None and municipio_idx is not None:
            mun_cand = dest_lines[municipio_idx].strip()
            # Clean times (ex: 'CAMPINA GRANDE 11:49:04' ou 'NATAL 10:07:34') -> remove timestamps
            mun_cand = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '', mun_cand).strip()
            # Evita que o candidato seja o endereço, telefones, ceps
            # Município geralmente tem mais de 3 chars e poucos dígitos
            if (len(mun_cand) > 3 and not is_cep(mun_cand) and 
                # Aceita se não tiver muitos dígitos (exceto timestamp já removido)
                len(re.findall(r'\d', mun_cand)) <= 2 and
                # Não é uma label de campo
                not re.match(r'^(FONE|TELEFONE|CEP|BAIRRO|MUNICIPIO|MUNIC)', mun_cand, re.IGNORECASE)):
                data['cidade_estado_destinatario'] = f"{mun_cand.upper()}/{dest_lines[uf_idx].strip().upper()}"

        # Para o bairro, procuramos uma linha entre addr_idx e municipio_idx
        # Importante: bairro geralmente vem DEPOIS do endereço e ANTES do município
        bairro_found = None
        search_start = addr_idx + 1 if addr_idx is not None else 0
        # Para 1 linha antes do município (ou onde estimamos que esteja)
        search_end = municipio_idx if municipio_idx is not None else (uf_idx - 1 if uf_idx is not None else min(len(dest_lines), search_start + 6))

        for j in range(search_start, search_end):
            candidate = dest_lines[j].strip()
            if not candidate:
                continue
            # descartes comuns
            if is_cep(candidate):
                continue
            if re.search(r'\d{2}:\d{2}:\d{2}', candidate):
                continue
            if re.search(r'^(FONE|TELEFONE|CEP|CNPJ|INSCRIÇÃO|INSCRICAO|DATA)', candidate, re.IGNORECASE):
                continue
            # evitar capturar data (formato dd/mm/yyyy)
            if re.search(r'\d{2}/\d{2}/\d{4}', candidate):
                continue
            # candidate plausível para bairro: nome entre 3-40 chars, sem UF
            if 3 < len(candidate) < 40 and not re.search(r'\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b', candidate):
                bairro_found = candidate
                break

        if bairro_found:
            data['bairro_destinatario'] = bairro_found.upper()
    
    # --- MUNICÍPIO/UF DESTINATÁRIO ---
    # Nota: município/UF já foi extraído na seção de bairro acima usando a lógica genérica
    # (busca UF nas linhas após endereço, município na linha anterior à UF)
    # Não são necessárias estratégias específicas por cidade
    
    # --- CEP DESTINATÁRIO ---
    # Procura CEP no bloco destinatário (geralmente aparece depois do endereço)
    ceps_dest = re.findall(r'\b(\d{5}[-]\d{3})\b', dest_block)
    if ceps_dest:
        # Pega o último (geralmente é do destinatário)
        data['cep_destinatario'] = ceps_dest[-1]
        
        # Consulta ViaCEP para preencher bairro, município e UF automaticamente
        viacep_data = consultar_viacep(ceps_dest[-1])
        if viacep_data:
            # Sobrescreve bairro e município/UF com dados do ViaCEP (mais confiável)
            if viacep_data.get('bairro'):
                data['bairro_destinatario'] = viacep_data['bairro'].upper()
            if viacep_data.get('municipio') and viacep_data.get('uf'):
                data['cidade_estado_destinatario'] = f"{viacep_data['municipio'].upper()}/{viacep_data['uf'].upper()}"
    
    # --- VOLUME ---
    # Procura QUANTIDADE no bloco TRANSPORTADOR (ex: "3" para virar "1/3")
    transport_section = text[text.find('TRANSPORTADOR'):] if 'TRANSPORTADOR' in text else text
    
    # Procura linha com QUANTIDADE seguida de número
    m = re.search(r'QUANTIDADE[^\d]*(\d+)', transport_section, re.IGNORECASE)
    if m:
        qtd = m.group(1)
        data['volume'] = f'1/{qtd}'
    else:
        data['volume'] = '1/1'
    
    # --- TRANSPORTE ---
    # Procura bloco TRANSPORTADOR e extrai o nome da transportadora
    transport_section = text[text.find('TRANSPORTADOR'):] if 'TRANSPORTADOR' in text else text
    
    # Estratégia: Procura padrões específicos de transportadoras conhecidas
    # Usa word boundary (\b) para evitar capturar prefixos indesejados como "caixa"
    transport_patterns = [
        # Padrão 1: Nomes específicos de transportadoras conhecidas (mais específico primeiro)
        r'\b(POTIGUAR|BRASPRESS|RIOGRANDELOG|JADLOG|SEQUOIA|JAMEF|AZUL\s+CARGO)\b',
        # Padrão 2: Nome seguido de TRANSPORTES (captura só o nome antes de TRANSPORTES)
        r'\b([A-Z]{4,})\s+TRANSPORTES',
        # Padrão 3: Nome terminando com LOG seguido de TRANSPORTES ou LTDA
        r'\b([A-Z]{4,}LOG)\b(?=\s+(?:TRANSPORTES|LTDA))',
    ]
    
    transport_found = False
    for pattern in transport_patterns:
        m = re.search(pattern, transport_section, re.IGNORECASE)
        if m:
            transport_name = m.group(1).strip()
            # Remove espaços múltiplos
            transport_name = re.sub(r'\s+', ' ', transport_name)
            data['transporte'] = transport_name.upper()
            transport_found = True
            break
    
    # Fallback: se nenhum padrão funcionou, tenta extrair da linha após TRANSPORTADOR
    if not transport_found:
        lines_after = [l.strip() for l in transport_section.split('\n') if l.strip()]
        for i, line in enumerate(lines_after):
            if 'TRANSPORTADOR' in line and i + 1 < len(lines_after):
                candidate = lines_after[i + 1]
                # Valida: não é endereço, não é CEP, não é telefone, não é label
                if (len(candidate) > 3 and 
                    not re.match(r'^(RUA|R\s|TV|AV|AVENIDA|CEP|FONE)', candidate, re.IGNORECASE) and
                    not re.search(r'\d{5}[-]\d{3}', candidate) and
                    not re.search(r'\d{4,5}[-\s]\d{4}', candidate) and
                    not re.match(r'^(QUANTIDADE|ESPECIE|MARCA|NUMERO)', candidate, re.IGNORECASE)):
                    # Remove palavras comuns que aparecem antes do nome da transportadora
                    candidate_clean = re.sub(r'^(caixa|embalagem|pacote)\s+', '', candidate, flags=re.IGNORECASE)
                    # Pega primeira palavra válida (mínimo 4 caracteres)
                    words = candidate_clean.split()
                    for word in words:
                        if len(word) >= 4 and word.isalpha():
                            data['transporte'] = word.upper()
                            transport_found = True
                            break
                if transport_found:
                    break
        
        # Se ainda não achou, deixa vazio
        if not transport_found:
            data['transporte'] = ''
    
    # --- CRIAR OBJETO ---
    try:
        etiqueta = EtiquetaData(
            nome_empresa=data.get('nome_empresa', ''),
            endereco_empresa=data.get('endereco_empresa', ''),
            cidade_estado_empresa=data.get('cidade_estado_empresa', ''),
            cep_empresa=data.get('cep_empresa', ''),
            numero_nf=data.get('numero_nf', ''),
            nome_destinatario=data.get('nome_destinatario', ''),
            endereco_destinatario=data.get('endereco_destinatario', ''),
            bairro_destinatario=data.get('bairro_destinatario', ''),
            cidade_estado_destinatario=data.get('cidade_estado_destinatario', ''),
            cep_destinatario=data.get('cep_destinatario', ''),
            volume=data.get('volume', '1/1'),
            transporte=data.get('transporte', '')
        )
        return etiqueta
    except Exception as e:
        st.error(f"Erro ao criar objeto EtiquetaData: {e}")
        return None

# ==================== GERADOR DE ETIQUETAS ====================

def gerar_pdf_etiquetas(etiquetas: List[EtiquetaData], output_path: str = None) -> bytes:
    """
    Gera PDF com etiquetas otimizado para folha A4.
    Layout: 2 colunas x 3 linhas = 6 etiquetas por página
    Expande etiquetas baseado no volume (ex: 1/3 gera 3 etiquetas).
    """
    # Expande as etiquetas com base no volume
    etiquetas_expandidas = []
    for etiqueta in etiquetas:
        # Extrai quantidade do volume (ex: "1/3" -> 3)
        volume_match = re.search(r'(\d+)/(\d+)', etiqueta.volume)
        if volume_match:
            quantidade = int(volume_match.group(2))
        else:
            quantidade = 1
        
        # Adiciona N cópias da etiqueta (cada uma com volume atualizado)
        for i in range(1, quantidade + 1):
            # Cria nova etiqueta com volume correto (1/3, 2/3, 3/3)
            etiqueta_copia = EtiquetaData(
                nome_empresa=etiqueta.nome_empresa,
                endereco_empresa=etiqueta.endereco_empresa,
                cidade_estado_empresa=etiqueta.cidade_estado_empresa,
                cep_empresa=etiqueta.cep_empresa,
                numero_nf=etiqueta.numero_nf,
                nome_destinatario=etiqueta.nome_destinatario,
                endereco_destinatario=etiqueta.endereco_destinatario,
                bairro_destinatario=etiqueta.bairro_destinatario,
                cidade_estado_destinatario=etiqueta.cidade_estado_destinatario,
                cep_destinatario=etiqueta.cep_destinatario,
                volume=f'{i}/{quantidade}',
                transporte=etiqueta.transporte
            )
            etiquetas_expandidas.append(etiqueta_copia)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    
    # Configurações de layout
    page_w = 210  # A4 width mm
    page_h = 297  # A4 height mm
    margin = 8
    col_spacing = 6
    row_spacing = 6
    
    # 2 colunas, 3 linhas (tamanho balanceado)
    cols = 2
    rows_per_page = 3
    etiquetas_per_page = cols * rows_per_page
    
    # Calcular dimensões das etiquetas
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin
    
    etiqueta_w = (usable_w - (cols - 1) * col_spacing) / cols
    etiqueta_h = (usable_h - (rows_per_page - 1) * row_spacing) / rows_per_page
    
    # Configurações de texto
    line_height_small = 5.0    # 12-13px com espaçamento
    line_height_medium = 5.5   # 14px com espaçamento  
    line_height_company = 6.0  # 14-15px (empresa) com espaçamento
    line_height_nf = 13        # 32px (NF destaque)
    padding = 3.5
    line_spacing = 0.4         # Espaçamento extra entre linhas
    
    # Processar cada etiqueta (agora usando etiquetas_expandidas)
    for idx, etiqueta in enumerate(etiquetas_expandidas):
        # Adicionar nova página se necessário
        if idx % etiquetas_per_page == 0:
            pdf.add_page()
        
        # Calcular posição
        pos_in_page = idx % etiquetas_per_page
        row = pos_in_page // cols
        col = pos_in_page % cols
        
        x = margin + col * (etiqueta_w + col_spacing)
        y = margin + row * (etiqueta_h + row_spacing)
        
        # Desenhar borda
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.33)
        pdf.rect(x, y, etiqueta_w, etiqueta_h)
        
        # Escrever conteúdo
        current_y = y + padding
        text_w = etiqueta_w - 2 * padding
        
        # Função auxiliar para quebrar texto em múltiplas linhas
        def wrap_text(text: str, max_width: float, font_size: int) -> list:
            """Quebra texto em múltiplas linhas se necessário"""
            pdf.set_font("Arial", "", font_size)
            
            # Se cabe em uma linha, retorna como está
            if pdf.get_string_width(text) <= max_width:
                return [text]
            
            # Quebra por palavras
            words = text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if pdf.get_string_width(test_line) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            return lines if lines else [text[:50] + "..."]  # Fallback
        
        # Função auxiliar para adicionar linha (com suporte a quebra)
        def add_line(text: str, size: int, bold: bool = False, height: float = None, extra_spacing: bool = True, force: bool = False):
            nonlocal current_y
            
            if height is None:
                height = line_height_small
            
            # Verifica overflow apenas se não for forçado
            if not force and current_y + height > y + etiqueta_h - padding:
                return  # Evitar overflow
            
            pdf.set_xy(x + padding, current_y)
            
            if bold:
                pdf.set_font("Arial", "B", size)
            else:
                pdf.set_font("Arial", "", size)
            
            # Quebra texto em múltiplas linhas se necessário
            text_upper = text.upper()
            lines = wrap_text(text_upper, text_w, size)
            
            # Escreve cada linha
            for i, line in enumerate(lines):
                # Se forçado, escreve mesmo se estourar o espaço
                if not force and current_y + height > y + etiqueta_h - padding:
                    break  # Para se não couber
                
                pdf.set_xy(x + padding, current_y)
                if bold:
                    pdf.set_font("Arial", "B", size)
                else:
                    pdf.set_font("Arial", "", size)
                
                pdf.cell(text_w, height, line, ln=0)
                current_y += height
            
            # Adiciona espaçamento extra entre campos diferentes (não entre linhas do mesmo campo)
            if extra_spacing:
                current_y += line_spacing
        
        # REMETENTE (empresa) - 12px bold
        add_line(etiqueta.nome_empresa, 11, bold=True, height=line_height_company)
        add_line(etiqueta.endereco_empresa, 11, height=line_height_small)
        add_line(f"{etiqueta.cidade_estado_empresa} - CEP: {etiqueta.cep_empresa}", 11, height=line_height_small)
        
        # Espaço entre seções
        current_y += 2.5
        
        # NF em destaque - 32px bold
        add_line(f"NF: {etiqueta.numero_nf.zfill(4)}", 32, bold=True, height=line_height_nf, extra_spacing=False)
        
        # Espaço após NF
        current_y += 2.5
        
        # DESTINATÁRIO - 12px
        add_line(etiqueta.nome_destinatario, 11, height=line_height_small)
        add_line(etiqueta.endereco_destinatario, 11, height=line_height_small)
        add_line(f"BAIRRO: {etiqueta.bairro_destinatario}", 11, height=line_height_small)
        add_line(f"{etiqueta.cidade_estado_destinatario}", 11, height=line_height_small, extra_spacing=False)
        
        # CEP e VOLUME na mesma linha (com espaçamento)
        current_y += line_spacing
        pdf.set_xy(x + padding, current_y)
        pdf.set_font("Arial", "", 11)
        cep_volume = f"CEP: {etiqueta.cep_destinatario}  VOLUME: {etiqueta.volume}"
        pdf.cell(text_w, line_height_small, cep_volume.upper(), ln=0)
        current_y += line_height_small
        
        # Espaço antes do transporte
        current_y += 2.0
        
        # TRANSPORTE - 12px (forçado para sempre aparecer)
        add_line(f"TRANSPORTE: {etiqueta.transporte}", 11, height=line_height_small, extra_spacing=False, force=True)
    
    # Retornar bytes do PDF
    if output_path:
        pdf.output(output_path)
        with open(output_path, 'rb') as f:
            return f.read()
    else:
        # Gerar em memória e retornar bytes
        pdf_bytes = pdf.output(dest='S')
        # pyfpdf/fpdf may return str, bytes, bytearray or memoryview depending on version.
        # Normalizamos para bytes para evitar erros downstream (ex: Streamlit download_button)
        if isinstance(pdf_bytes, str):
            return pdf_bytes.encode('latin-1')
        if isinstance(pdf_bytes, (bytearray, memoryview)):
            return bytes(pdf_bytes)
        if isinstance(pdf_bytes, bytes):
            return pdf_bytes

        # Fallback: tente converter para bytes
        try:
            return bytes(pdf_bytes)
        except Exception:
            # Como último recurso, converte a representação para latin-1
            try:
                return str(pdf_bytes).encode('latin-1')
            except Exception:
                # Retorna objeto vazio para evitar crash inesperado
                return b''

# ==================== STREAMLIT APP ====================

def main():
    st.set_page_config(
        page_title="Gerador de Etiquetas Correios",
        page_icon="📦",
        layout="wide"
    )
    
    st.title("📦 Gerador de Etiquetas para Correios")
    st.markdown("---")
    
    # Sidebar com instruções
    with st.sidebar:
        st.header("📋 Instruções")
        st.markdown("""
        1. **Upload**: Carregue um ou mais arquivos PDF de NF-e
        2. **Revisão**: Confira os dados extraídos automaticamente
        3. **Edição**: Corrija qualquer campo se necessário
        4. **Geração**: Clique em "Gerar Etiquetas" para criar o PDF
        5. **Download**: Baixe o PDF com todas as etiquetas
        
        **Formato:**
        - 6 etiquetas por folha A4 (2x3) - tamanho otimizado
        - Múltiplos PDFs são processados juntos
        - Otimização automática de folhas
        - Todas as informações cabem na etiqueta
        """)
        
        st.markdown("---")
        st.info("💡 O sistema detecta automaticamente todos os campos da NF-e")
    
    # Upload de arquivos (múltiplos)
    st.header("1️⃣ Upload de Arquivos NF-e")
    uploaded_files = st.file_uploader(
        "Selecione um ou mais arquivos PDF",
        type=['pdf'],
        accept_multiple_files=True,
        help="Você pode selecionar múltiplos arquivos de uma vez"
    )
    
    if not uploaded_files:
        st.info("👆 Faça upload de pelo menos um arquivo PDF de NF-e para começar")
        return
    
    st.success(f"✅ {len(uploaded_files)} arquivo(s) carregado(s)")
    
    # Processar arquivos e extrair dados
    st.header("2️⃣ Dados Extraídos")
    
    # Armazenar etiquetas no session state
    if 'etiquetas' not in st.session_state or st.button("🔄 Re-processar PDFs"):
        etiquetas_extraidas = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processando {uploaded_file.name}...")
            
            # Extrair texto
            text = extract_text_from_pdf(uploaded_file)
            
            if text:
                # Parsear dados
                etiqueta = parse_nfe_data(text)
                if etiqueta:
                    etiquetas_extraidas.append({
                        'filename': uploaded_file.name,
                        'data': etiqueta
                    })
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.empty()
        progress_bar.empty()
        
        st.session_state.etiquetas = etiquetas_extraidas
    
    if not st.session_state.etiquetas:
        st.error("❌ Nenhum dado foi extraído dos PDFs. Verifique se os arquivos são NF-e válidas.")
        return
    
    st.success(f"✅ {len(st.session_state.etiquetas)} etiqueta(s) extraída(s)")
    
    # Preview e edição das etiquetas
    st.header("3️⃣ Revisão e Edição")
    
    etiquetas_editadas = []
    
    for idx, item in enumerate(st.session_state.etiquetas):
        with st.expander(f"📄 {item['filename']} - NF: {item['data'].numero_nf}", expanded=False):
            cols = st.columns(2)
            
            with cols[0]:
                st.subheader("Remetente (Empresa)")
                nome_empresa = st.text_input(
                    "Nome da Empresa",
                    value=item['data'].nome_empresa,
                    key=f"nome_empresa_{idx}"
                )
                endereco_empresa = st.text_input(
                    "Endereço",
                    value=item['data'].endereco_empresa,
                    key=f"endereco_empresa_{idx}"
                )
                cidade_estado_empresa = st.text_input(
                    "Cidade/Estado",
                    value=item['data'].cidade_estado_empresa,
                    key=f"cidade_estado_empresa_{idx}"
                )
                cep_empresa = st.text_input(
                    "CEP",
                    value=item['data'].cep_empresa,
                    key=f"cep_empresa_{idx}"
                )
                
                st.markdown("---")
                numero_nf = st.text_input(
                    "Número NF",
                    value=item['data'].numero_nf,
                    key=f"numero_nf_{idx}"
                )
                volume = st.text_input(
                    "Volume",
                    value=item['data'].volume,
                    key=f"volume_{idx}",
                    help="Formato: 1/1, 1/3, etc"
                )
                transporte = st.text_input(
                    "Transporte",
                    value=item['data'].transporte,
                    key=f"transporte_{idx}"
                )
                # Debug temporário: mostrar valor extraído
                if item['data'].transporte:
                    st.caption(f"✓ Extraído: {item['data'].transporte}")
                else:
                    st.warning("⚠️ Transporte não foi extraído do PDF")
            
            with cols[1]:
                st.subheader("Destinatário")
                nome_destinatario = st.text_input(
                    "Nome",
                    value=item['data'].nome_destinatario,
                    key=f"nome_destinatario_{idx}"
                )
                endereco_destinatario = st.text_input(
                    "Endereço",
                    value=item['data'].endereco_destinatario,
                    key=f"endereco_destinatario_{idx}"
                )
                bairro_destinatario = st.text_input(
                    "Bairro",
                    value=item['data'].bairro_destinatario,
                    key=f"bairro_destinatario_{idx}"
                )
                cidade_estado_destinatario = st.text_input(
                    "Cidade/Estado",
                    value=item['data'].cidade_estado_destinatario,
                    key=f"cidade_estado_destinatario_{idx}"
                )
                cep_destinatario = st.text_input(
                    "CEP",
                    value=item['data'].cep_destinatario,
                    key=f"cep_destinatario_{idx}"
                )
            
            # Criar etiqueta editada
            etiqueta_editada = EtiquetaData(
                nome_empresa=nome_empresa,
                endereco_empresa=endereco_empresa,
                cidade_estado_empresa=cidade_estado_empresa,
                cep_empresa=cep_empresa,
                numero_nf=numero_nf,
                nome_destinatario=nome_destinatario,
                endereco_destinatario=endereco_destinatario,
                bairro_destinatario=bairro_destinatario,
                cidade_estado_destinatario=cidade_estado_destinatario,
                cep_destinatario=cep_destinatario,
                volume=volume,
                transporte=transporte
            )
            etiquetas_editadas.append(etiqueta_editada)
    
    # Geração de etiquetas
    st.markdown("---")
    st.header("4️⃣ Gerar PDF")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        total_etiquetas = len(etiquetas_editadas)
        total_paginas = (total_etiquetas + 5) // 6  # 6 etiquetas por página
        
        st.info(f"📊 **Total:** {total_etiquetas} etiqueta(s) em {total_paginas} página(s)")
        
        if st.button("🎨 Gerar Etiquetas", type="primary", use_container_width=True):
            with st.spinner("Gerando PDF..."):
                try:
                    pdf_bytes = gerar_pdf_etiquetas(etiquetas_editadas)
                    
                    st.success("✅ PDF gerado com sucesso!")
                    
                    # Botão de download
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name="etiquetas_correios.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar PDF: {e}")

if __name__ == "__main__":
    main()
