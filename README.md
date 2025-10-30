# Gerador de Etiquetas para Correios

Sistema Streamlit para processamento de múltiplas NF-e e geração automatizada de etiquetas para Correios.

## ✨ Funcionalidades

### Requisitos Funcionais Implementados

- ✅ **Recebe PDFs de NF-e**: Upload de um ou múltiplos arquivos PDF
- ✅ **Extração Automática**: Detecta automaticamente todos os campos:
  - **Remetente (Empresa)**: Nome, Endereço, Cidade/Estado, CEP
  - **Nota Fiscal**: Número da NF
  - **Destinatário**: Nome, Endereço, Bairro, Cidade/Estado, CEP
  - **Logística**: Volume (1/1, 1/3, etc), Transportadora
- ✅ **Geração de PDF**: Cria PDF otimizado com etiquetas prontas para impressão
- ✅ **Preview e Edição**: Interface para revisar e corrigir dados antes da geração

### Requisitos Não-Funcionais Implementados

- ✅ **Somente PDF**: Sistema aceita apenas arquivos .pdf
- ✅ **Múltiplos Arquivos**: Processa vários PDFs em uma única operação
- ✅ **Otimização de Folhas A4**:
  - 6 etiquetas por página (layout 2x3)
  - Quebra automática de página
  - Combina etiquetas de múltiplos PDFs na mesma folha
  - Exemplo: 9 etiquetas = 6 na página 1 + 3 na página 2
- ✅ **Preview no Frontend**: Streamlit mostra todos os campos extraídos para validação/correção

## 📦 Instalação

```powershell
# 1. Instalar dependências
pip install streamlit pypdf fpdf2

# Ou usando requirements.txt
pip install -r requirements.txt
```

## 🚀 Como Usar

### 1. Iniciar o Servidor

```powershell
cd streamlit-etiquetas-correios
streamlit run app.py
```

O sistema abrirá automaticamente em: http://localhost:8501

### 2. Fluxo de Uso

1. **Upload**: 
   - Clique em "Browse files"
   - Selecione um ou mais PDFs de NF-e
   - Pode usar Ctrl+Click para selecionar múltiplos arquivos

2. **Processamento Automático**:
   - Sistema extrai texto de todos os PDFs
   - Detecta automaticamente os campos conforme imagem fornecida
   - Mostra barra de progresso durante processamento

3. **Revisão**:
   - Cada NF-e aparece em um expander
   - Todos os campos são editáveis
   - Corrija qualquer erro de extração se necessário

4. **Geração**:
   - Clique em "Gerar Etiquetas"
   - Sistema cria PDF otimizado
   - 6 etiquetas por folha A4 (2 colunas x 3 linhas)

5. **Download**:
   - Clique em "Download PDF"
   - Arquivo pronto para impressão

## 📐 Layout das Etiquetas

Cada etiqueta contém (conforme imagem):

```
┌─────────────────────────────┐
│ REMETENTE: [Nome Empresa]   │
│ END: [Endereço Empresa]     │
│ [Cidade-UF] - CEP: [CEP]    │
│                             │
│ NF: [Número]                │
│                             │
│ DEST: [Nome Destinatário]   │
│ END: [Endereço]             │
│ BAIRRO: [Bairro]            │
│ [Cidade-UF]                 │
│ CEP: [CEP]                  │
│                             │
│ VOLUME: [1/1]               │
│ TRANSPORTE: [Nome]          │
└─────────────────────────────┘
```

## 🎯 Exemplos de Uso

### Caso 1: Single NF-e
- Upload: 1 arquivo PDF
- Resultado: 1 etiqueta (1 página)

### Caso 2: Múltiplas NF-e (otimizado)
- Upload: 4 arquivos PDF
- Resultado: 4 etiquetas (1 página com 4 etiquetas)

### Caso 3: Múltiplas NF-e (com quebra)
- Upload: 9 arquivos PDF
- Resultado: 9 etiquetas (2 páginas: 6 + 3)

### Caso 4: Mix de volumes
- Upload: PDFs com VOLUME 1/3 cada
- Resultado: 3 etiquetas por PDF automaticamente

## 🔧 Troubleshooting

### Campos não detectados?
- Use o formulário de edição para preencher manualmente
- Verifique se o PDF é texto (não imagem escaneada)

### Layout desconfigurado?
- O sistema está otimizado para A4
- 6 etiquetas por página é o ideal para corte

### Erro ao processar PDF?
- Certifique-se que é uma NF-e válida (DANFE)
- Arquivo deve ter texto extraível

## 📊 Estrutura do Projeto

```
streamlit-etiquetas-correios/
├── app.py              # Aplicação principal
├── requirements.txt    # Dependências
└── README.md          # Documentação
```

## 🎨 Features Extras

- 📊 Contador de etiquetas e páginas
- 🔄 Botão de re-processamento
- 📋 Instruções integradas na sidebar
- ✅ Validação visual com ícones
- 🎨 Interface moderna e intuitiva

## 📝 Observações Técnicas

### Extração de Dados
- Usa regex robustas adaptadas ao formato brasileiro de NF-e
- Isola blocos de REMETENTE e DESTINATÁRIO para melhor precisão
- Fallbacks múltiplos para cada campo

### Geração de PDF
- FPDF com layout responsivo
- Bordas de 0.5mm para facilitar corte
- Texto truncado automaticamente se exceder espaço
- Negrito em campos principais (Nome, NF, Volume)

### Performance
- Processa múltiplos PDFs em paralelo (barra de progresso)
- Session state do Streamlit para manter dados
- Geração sob demanda (não regenera a cada interação)

## 🚀 Melhorias Futuras Possíveis

- [ ] Export para planilha Excel
- [ ] Template customizável de etiquetas
- [ ] Código de barras nas etiquetas
- [ ] OCR para PDFs escaneados
- [ ] Histórico de etiquetas geradas
- [ ] API REST para integração

---

**Desenvolvido para otimizar o processo de envio pelos Correios com múltiplas NF-e** 📦✨
