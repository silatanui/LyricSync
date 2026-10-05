/**
 * Shared lyric font catalog for studio preview + picker labels.
 * Proprietary faces keep their family name and fall back to close system/web substitutes.
 */
window.LyricSyncFonts = {
    stacks: {
        Caveat: "'Caveat', cursive, sans-serif",
        Montserrat: "'Montserrat', sans-serif",
        'Bebas Neue': "'Bebas Neue', sans-serif",
        Oswald: "'Oswald', sans-serif",
        'Helvetica Neue': "'Helvetica Neue', Helvetica, Arial, sans-serif",
        Futura: "Futura, 'Trebuchet MS', Arial, sans-serif",
        Lato: "'Lato', sans-serif",
        Roboto: "'Roboto', sans-serif",
        'Open Sans': "'Open Sans', Arial, sans-serif",
        Inter: "'Inter', system-ui, sans-serif",
        'ITC Century': "'Century Schoolbook', Century, 'ITC Century', 'Times New Roman', serif",
        'Times New Roman': "'Times New Roman', Times, serif",
        'Minion Pro': "'Minion Pro', 'EB Garamond', Garamond, 'Times New Roman', serif",
        Georgia: "Georgia, 'Times New Roman', serif",
        Arial: "Arial, Helvetica, sans-serif",
        'Courier New': "'Courier New', Courier, monospace",
        Garamond: "'EB Garamond', Garamond, 'Times New Roman', serif",
        'Playfair Display': "'Playfair Display', Georgia, serif",
        'Source Sans Pro': "'Source Sans 3', 'Source Sans Pro', sans-serif",
        Raleway: "'Raleway', sans-serif",
        'Proxima Nova': "'Proxima Nova', Montserrat, 'Helvetica Neue', Arial, sans-serif",
        Poppins: "'Poppins', sans-serif",
        'League Spartan': "'League Spartan', 'Arial Narrow', Arial, sans-serif",
        Anton: "'Anton', Impact, sans-serif",
        Avenir: "Avenir, 'Avenir Next', 'Helvetica Neue', Arial, sans-serif",
        Univers: "Univers, 'Helvetica Neue', Arial, sans-serif",
        Bodoni: "'Bodoni Moda', 'Bodoni MT', Bodoni, Didot, serif",
        Baskerville: "Baskerville, 'Libre Baskerville', 'Times New Roman', serif",
        'Cormorant Garamond': "'Cormorant Garamond', Garamond, serif",
        Ubuntu: "'Ubuntu', sans-serif",
        'PT Sans': "'PT Sans', sans-serif",
        // Existing studio extras
        Outfit: "'Outfit', sans-serif",
        Cinzel: "'Cinzel', Georgia, serif",
        Merriweather: "'Merriweather', Georgia, serif",
        Nunito: "'Nunito', sans-serif",
        'DM Sans': "'DM Sans', sans-serif",
        'Libre Baskerville': "'Libre Baskerville', Baskerville, serif",
        'Trebuchet MS': "'Trebuchet MS', sans-serif",
        // Estelle is a script display name; Great Vibes is the open licensed face used for preview + export.
        Estelle: "'Great Vibes', 'Estelle', cursive",
        'Great Vibes': "'Great Vibes', cursive",
    },

    resolve(name) {
        const key = (name || 'Caveat').trim();
        return this.stacks[key] || `"${key}", sans-serif`;
    },
};
