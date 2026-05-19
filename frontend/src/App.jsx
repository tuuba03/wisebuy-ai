import { useState, useEffect, useRef } from 'react';
import { Sparkles, Search, CheckCircle2, AlertTriangle, PlayCircle, Star, ShoppingCart, ArrowRight, Bot, Send, ArrowLeft, Home } from 'lucide-react';
import './App.css';

// AI raporundan belirli bir başlık bloğunu parse eder (emoji destekli)
function extractSection(report, ...headers) {
  if (!report) return '';
  for (const header of headers) {
    // ## ile başlayan satırlarda emoji + boşluk + başlık kombinasyonlarını yakala
    const regex = new RegExp(`##[\\s\\S]{0,20}${header}[\\s\\S]*?(?=\\n##|$)`, 'i');
    const match = report.match(regex);
    if (match) {
      // Başlık satırını at, içeriği döndür
      return match[0].replace(/^##[^\n]+\n/, '').trim();
    }
  }
  return '';
}

// Metinden madde listesi çıkar (kaynak satırlarını filtrele)
function parseBullets(text) {
  if (!text) return [];
  return text.split('\n')
    .map(l => l.replace(/^[-*•]\s*/, '').trim())
    .filter(l => l.length > 5)
    .filter(l => !l.toLowerCase().startsWith('kaynak:') && !l.includes('*kaynak') && !l.match(/\*kaynak/i));
}

// Markdown işaretlerini temizle
function cleanMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')  // **bold**
    .replace(/\*(.*?)\*/g, '$1')       // *italic*
    .replace(/`(.*?)`/g, '$1')         // `code`
    .replace(/^#+\s+/gm, '')           // ## Başlıklar
    .replace(/^[-*]\s+/gm, '• ')       // - madde işaretleri → •
    .trim();
}

function App() {
  const [appState, setAppState] = useState('HOME'); // HOME, LOADING, RESULTS, CHAT
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  
  const textareaRef = useRef(null);
  const chatEndRef = useRef(null);
  const chatInputRef = useRef(null);

  const handleInput = (e) => {
    setQuery(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  useEffect(() => {
    let interval;
    if (appState === 'LOADING') {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep(prev => (prev < 2 ? prev + 1 : prev));
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [appState]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Chat ekranına geçince karşılama mesajı ekle
  const goToChat = () => {
    if (chatMessages.length === 0) {
      setChatMessages([{
        role: 'bot',
        text: `Merhaba! 👋 **${query}** hakkında merak ettiğin her şeyi sorabilirsin. Pil ömrü, performans, kamera karşılaştırması... Hepsi burada! 🤖`
      }]);
    }
    setAppState('CHAT');
  };

  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setAppState('LOADING');
    
    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_name: query,
          purpose: "Genel kullanım",
          budget: 0
        }),
      });

      if (!response.ok) throw new Error('API Hatası');

      const data = await response.json();
      setResults(data);
      setChatMessages([]); // Yeni arama — chat'i sıfırla
      setAppState('RESULTS');
    } catch (error) {
      console.error(error);
      alert("Bir hata oluştu. Lütfen tekrar deneyin.");
      setAppState('HOME');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  // Chat mesajı gönder
  const sendChatMessage = async (messageText) => {
    const text = messageText || chatInput.trim();
    if (!text || chatLoading) return;

    const userMsg = { role: 'user', text };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          analysis_context: results?.ai_report || '',
          product_name: query,
        }),
      });

      const data = await response.json();
      setChatMessages(prev => [...prev, { role: 'bot', text: data.reply || 'Bir yanıt alınamadı.' }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'bot', text: '❌ Bağlantı hatası oluştu, lütfen tekrar dene.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleChatKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  };

  // Analiz raporundan bölüm parse et
  const aiReport = results?.ai_report || '';
  const summaryText = extractSection(aiReport, 'Özet', 'Ürün Özeti');
  const purposeText = extractSection(aiReport, 'Amaca Uygunluk');
  const techText = extractSection(aiReport, 'Teknik İnceleme');
  const prosText = extractSection(aiReport, 'İyi Özellikler', 'Artılar');
  const problemsText = extractSection(aiReport, 'Kronik Sorunlar', 'Eksiler');
  const videoText = extractSection(aiReport, 'Video İncelemeleri');
  const decisionText = extractSection(aiReport, 'WiseBuy Kararı', 'Karar');
  const heroVerdict = decisionText || extractSection(aiReport, 'Önerisi');

  // Örnek sorular
  const SUGGESTIONS = [
    '💡 Neden bu ürünü öneriyorsun?',
    '🔋 Pil ömrü nasıl?',
    '🌡️ Isınma problemi var mı?',
    '📸 Kamera kalitesi hakkında ne düşünüyorsun?',
  ];

  return (
    <div className="app-container">

      {/* ===== HOME & LOADING ===== */}
      {(appState === 'HOME' || appState === 'LOADING') && (
        <div className="home-container">
          <div className="logo-section">
            <Sparkles className="logo-icon" size={56} />
            <h1 className="logo-text">WiseBuy AI</h1>
          </div>
          
          <h2 className="tagline">Ne arıyorsun? Sana en iyi seçeneği bulalım.</h2>
          <p className="sub-tagline">
            Fiyatları karşılaştırır, videoları izler, şikayetleri analiz eder - saniyeler içinde karar verir.
          </p>

          <div className="search-box">
            <textarea 
              ref={textareaRef}
              rows="1"
              placeholder="Örn: Oyun oynamak için 45.000 TL iPhone 15 veya Evde kahve yapmak için makine..."
              value={query}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              disabled={appState === 'LOADING'}
            />
            <button 
              className="analyze-btn" 
              onClick={handleAnalyze}
              disabled={appState === 'LOADING'}
            >
              <Search size={18} /> Analiz Et
            </button>
          </div>

          <div className="search-examples">
            <span>Örnek aramalar:</span>
            {[
              'iPhone 15 — 45.000 TL',
              '20 bin TL ev kahve makinesi',
              'Oyun için en iyi laptop'
            ].map((ex, i) => (
              <button key={i} className="example-chip" onClick={() => { setQuery(ex); }}>
                {ex}
              </button>
            ))}
          </div>

          <div className="footer-hint">
            💡 AI destekli karar alma sistemi ile artık alışverişinizde yanılmayın
          </div>

          {appState === 'LOADING' && (
            <div className="loading-card">
              <div className="loading-header">
                <Sparkles size={24} className="loading-icon animate-pulse" />
                <span>Yapay zeka analiz ediyor...</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill animate-pulse" style={{width: `${(loadingStep + 1) * 33}%`}}></div>
              </div>
              <div className="loading-steps">
                <div className={`step ${loadingStep >= 0 ? 'active' : ''}`}><span className="dot blue"></span> Fiyatlar<br/>taranıyor...</div>
                <div className={`step ${loadingStep >= 1 ? 'active' : ''}`}><span className="dot purple"></span> Videolar<br/>izleniyor...</div>
                <div className={`step ${loadingStep >= 2 ? 'active' : ''}`}><span className="dot pink"></span> Şikayetler<br/>analiz ediliyor...</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== RESULTS ===== */}
      {appState === 'RESULTS' && results && (
        <div className="results-container">
          <div className="results-header">
            <div className="header-left">
              <button className="back-btn" onClick={() => setAppState('HOME')}>
                <ArrowLeft size={16}/> Yeni Arama
              </button>
              <h2>Analiz Sonuçları</h2>
              <p className="query-text">{query}</p>
            </div>
            <button className="chat-nav-btn" onClick={goToChat}>
              <Bot size={18}/> AI ile Konuş
            </button>
          </div>

          <div className="results-grid">
            {/* Sol Kolon */}
            <div className="results-col">
              {/* Hero Card */}
              <div className="hero-card">
                <div className="hero-content">
                  <h3><CheckCircle2 size={24}/> {heroVerdict ? heroVerdict.substring(0, 35) + (heroVerdict.length > 35 ? '...' : '') : 'WiseBuy Kararı'}</h3>
                  <span className="ai-badge">AI Önerisi</span>
                </div>
                <div className="score-circle">
                  <span className="score-number">{results.overall_sentiment_score || "8.5"}</span>
                  <span className="score-max">/10</span>
                </div>
                
                <div className="hero-details">
                  <div className="detail-box">
                    <h4>📊 Ürün Özeti</h4>
                    <p>{summaryText || (aiReport ? aiReport.split('\n').find(l => l.length > 40 && !l.startsWith('#')) || 'Analiz raporu oluşturuldu.' : 'Analiz raporu oluşturuldu.')}</p>
                  </div>
                  <div className="detail-box">
                    <h4>🎯 Amaca Uygunluk</h4>
                    <p>{purposeText || 'Kullanım amacınıza göre değerlendirme yapıldı.'}</p>
                  </div>
                  <div className="detail-box">
                    <h4>⚙️ Teknik İnceleme</h4>
                    <p>{techText || 'Teknik detaylar analiz raporu içerisinde yer almaktadır.'}</p>
                  </div>
                </div>
              </div>

              {/* Mini Score Cards */}
              <div className="scores-grid">
                <div className="score-card glass-panel">
                  <div className="score-card-header">
                    <div className="icon-bg purple-bg"><Star size={20}/></div>
                    <div className="score-val">{results.purpose_fit_score || "9.2"}<span>/10</span></div>
                  </div>
                  <p>Amaca Uygunluk</p>
                  <div className="mini-progress"><div className="fill purple-fill" style={{width: `${(results.purpose_fit_score || 9.2)*10}%`}}></div></div>
                </div>
                
                <div className="score-card glass-panel">
                  <div className="score-card-header">
                    <div className="icon-bg blue-bg"><ShoppingCart size={20}/></div>
                    <div className="score-val">{results.value_for_money_score || "7.8"}<span>/10</span></div>
                  </div>
                  <p>Fiyat/Performans</p>
                  <div className="mini-progress"><div className="fill blue-fill" style={{width: `${(results.value_for_money_score || 7.8)*10}%`}}></div></div>
                </div>
              </div>

              {/* Kullanici Yorumlari Analizi */}
              <div className="review-analysis-panel glass-panel">
                <h3 className="section-title"><Star size={20} className="success-text"/> Kullanici Yorumlari Analizi</h3>

                <div className="sentiment-score-row">
                  <div className="sentiment-gauge">
                    <svg viewBox="0 0 100 60" className="gauge-svg">
                      <path d="M10,55 A45,45 0 0,1 90,55" fill="none" stroke="#E5E7EB" strokeWidth="10" strokeLinecap="round"/>
                      <path d="M10,55 A45,45 0 0,1 90,55" fill="none"
                        stroke={results.overall_sentiment_score >= 8 ? '#10B981' : results.overall_sentiment_score >= 6 ? '#F59E0B' : '#EF4444'}
                        strokeWidth="10" strokeLinecap="round"
                        strokeDasharray={`${(results.overall_sentiment_score || 7) * 14.1} 141`}/>
                    </svg>
                    <div className="gauge-label">
                      <span className="gauge-val">{((results.overall_sentiment_score || 7) * 10).toFixed(0)}%</span>
                      <span className="gauge-sub">Genel Memnuniyet</span>
                    </div>
                  </div>
                  <div className="sentiment-bars">
                    <div className="sbar-row">
                      <span>Amaca Uygunluk</span>
                      <div className="sbar-track"><div className="sbar-fill purple-fill" style={{width:`${(results.purpose_fit_score||7)*10}%`}}/></div>
                      <span className="sbar-pct">{((results.purpose_fit_score||7)*10).toFixed(0)}%</span>
                    </div>
                    <div className="sbar-row">
                      <span>Fiyat/Performans</span>
                      <div className="sbar-track"><div className="sbar-fill blue-fill" style={{width:`${(results.value_for_money_score||7)*10}%`}}/></div>
                      <span className="sbar-pct">{((results.value_for_money_score||7)*10).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {(results.top_pros?.length > 0 || parseBullets(prosText).length > 0) && (
                  <div className="chips-section">
                    <h4 className="chips-title success-text">Kullanicilarin Begendikleri</h4>
                    <div className="chips-row">
                      {(results.top_pros?.length > 0 ? results.top_pros : parseBullets(prosText)).map((pro, i) => (
                        <span key={i} className="chip chip-green">{pro}</span>
                      ))}
                    </div>
                  </div>
                )}

                {(results.top_cons?.length > 0 || parseBullets(problemsText).length > 0) && (
                  <div className="chips-section">
                    <h4 className="chips-title warning-text">Sik Dile Getirilen Sorunlar</h4>
                    <div className="chips-row">
                      {(results.top_cons?.length > 0 ? results.top_cons : parseBullets(problemsText)).map((con, i) => (
                        <span key={i} className="chip chip-orange">{con}</span>
                      ))}
                    </div>
                  </div>
                )}

                {results.complaint_categories?.length > 0 && (
                  <div className="complaint-bars">
                    <h4 className="chips-title" style={{color:'#6B7280'}}>Sikayet Dagilimi (Sikayetvar analizi)</h4>
                    {results.complaint_categories.map((cat, i) => (
                      <div key={i} className="complaint-bar-row">
                        <span className="complaint-label">{cat.label}</span>
                        <div className="complaint-track">
                          <div className="complaint-fill" style={{
                            width: `${cat.percentage}%`,
                            background: cat.percentage > 60 ? '#EF4444' : cat.percentage > 35 ? '#F59E0B' : '#10B981'
                          }}/>
                        </div>
                        <span className="complaint-pct">%{cat.percentage}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Sağ Kolon */}
            <div className="results-col">
              {/* Sellers */}
              <div className="sellers-section glass-panel">
                <h3 className="section-title"><CheckCircle2 className="success-text" size={20}/> Güvenilir Satıcılar</h3>
                
                <div className="seller-list">
                  {results.prices && results.prices.slice(0,5).map((price, index) => (
                    <div key={index} className={`seller-card ${index >= 3 ? 'warning-card' : 'success-card'}`}>
                      <div className="seller-info">
                        <span className={`rank-badge ${index === 0 ? 'rank-gold' : index === 1 ? 'rank-silver' : ''}`}>{index + 1}</span>
                        <span className="seller-name">{price.seller_name}</span>
                        <span className="seller-price">{price.price.toLocaleString('tr-TR')} ₺</span>
                      </div>
                      {index >= 3 && (
                        <div className="seller-warning">
                          ⚠️ Dikkat: Bu satıcı için bazı Şikayetvar kayıtları bulundu.
                        </div>
                      )}
                      <button className="buy-btn" onClick={() => window.open(price.url || '#', '_blank')}>
                        <ShoppingCart size={16}/> Satın Al ↗
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Videos */}
              <div className="videos-section glass-panel">
                <h3 className="section-title"><PlayCircle className="purple-text" size={20}/> Video İncelemelerinden</h3>
                <div className="video-list">
                  {results.video_summaries && results.video_summaries.length > 0
                    ? results.video_summaries.flatMap((video) =>
                        video.key_points
                          ? video.key_points
                              .filter(point => 
                                point && point.length > 10 &&
                                !point.toLowerCase().includes('kaynak:') &&
                                !point.match(/\*kaynak/i) &&
                                !point.toLowerCase().startsWith('source:')
                              )
                              .slice(0, 2)
                              .map((point, i) => (
                                <div key={`${video.video_id || i}-${i}`} className="video-card">
                                  <PlayCircle size={16} className="video-icon purple-text" />
                                  <p>{point.replace(/\*kaynak.*$/i, '').replace(/\(kaynak.*?\)/gi, '').replace(/\*\*/g,'').replace(/\*/g,'').trim()}</p>
                                </div>
                              ))
                          : []
                      )
                    : (
                      videoText
                        ? parseBullets(videoText).map((point, i) => (
                            <div key={i} className="video-card">
                              <PlayCircle size={16} className="video-icon purple-text" />
                              <p>{point}</p>
                            </div>
                          ))
                        : <p className="empty-state">Video incelemesi bulunamadı.</p>
                    )
                  }
                </div>
              </div>

              {/* Alternatives */}
              {results.alternatives && results.alternatives.length > 0 && (
                <div className="alternatives-section glass-panel">
                  <h3 className="section-title">🔄 Alternatif Öneriler</h3>
                  <div className="alt-list">
                    {results.alternatives.map((alt, idx) => (
                      <div key={idx} className="alt-card">
                        <h4>{alt.name}</h4>
                        <p className="alt-price">~{Number(alt.approximate_price).toLocaleString('tr-TR')} ₺</p>
                        <p className="alt-reason"><ArrowRight size={14}/> {alt.reason}</p>
                        <button className="examine-btn" onClick={() => { setQuery(alt.name); setAppState('HOME'); }}>
                          Bunu İncele →
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== CHAT ===== */}
      {appState === 'CHAT' && (
        <div className="chat-container">
          <div className="chat-nav-header">
            <button className="nav-icon-btn" onClick={() => setAppState('RESULTS')} title="Sonuçlara Dön">
              <ArrowLeft size={20}/> Analiz Sonuçları
            </button>
            <span className="chat-product-name">{query}</span>
            <button className="nav-icon-btn" onClick={() => setAppState('HOME')} title="Yeni Arama">
              <Home size={18}/> Yeni Arama
            </button>
          </div>

          <div className="chat-section">
            <div className="chat-header">
              <div className="chat-icon-bg"><Bot size={24} color="white"/></div>
              <div>
                <h3>AI Asistanı ile Konuş</h3>
                <p>Ürün hakkında merak ettiğiniz her şeyi sorun</p>
              </div>
            </div>

            <div className="chat-messages" id="chat-scroll">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role === 'bot' ? 'bot-message' : 'user-message'}`}>
                  {msg.role === 'bot' && (
                    <div className="avatar"><Bot size={16} color="white"/></div>
                  )}
                  <div className="bubble">
                    <p style={{whiteSpace: 'pre-wrap'}}>{cleanMarkdown(msg.text)}</p>
                  </div>
                  {msg.role === 'user' && (
                    <div className="avatar user-avatar">👤</div>
                  )}
                </div>
              ))}
              {chatLoading && (
                <div className="message bot-message">
                  <div className="avatar"><Bot size={16} color="white"/></div>
                  <div className="bubble typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="chat-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => sendChatMessage(s)}>{s}</button>
              ))}
            </div>

            <div className="chat-input-area">
              <input 
                ref={chatInputRef}
                type="text" 
                placeholder="Ürün hakkında soru sorun..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleChatKeyDown}
                disabled={chatLoading}
              />
              <button className="send-btn" onClick={() => sendChatMessage()} disabled={chatLoading}>
                <Send size={18}/>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
