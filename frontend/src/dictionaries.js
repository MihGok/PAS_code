// src/dictionaries.js (без изменений, как в предыдущем ответе)

// --- Словарь: Код -> Полное название (для отображения) ---
export const diseaseMap = {
    'BKL': 'Доброкачественные кератозоподобные поражения', // Benign Keratosis-like lesions
    'AK': 'Актинический кератоз',                        // Actinic Keratoses
    'BCC': 'Базально-клеточная карцинома',               // Basal Cell Carcinoma
    'DF': 'Дерматофиброма',                              // Dermatofibroma
    'NV': 'Меланоцитарные невусы',                       // Melanocytic Nevi
    'NV_M': 'Меланоцитарные невусы',                     // Старый код 'NV'
    'VASC': 'Сосудистые поражения',                      // Vascular lesions
    'MEL': 'Меланома'                                    // Melanoma
};

// --- Словарь: Код -> Полное название (для отображения) ---
export const locationMap = {
    'UE': 'Верхняя конечность', // Upper extremity
    'UK': 'Неизвестно',         // Unknown
    'SC': 'Волосистая часть головы', // Scalp
    'GE': 'Гениталии',          // Genital
    'NK': 'Шея',                // Neck
    'LE': 'Нижняя конечность',  // Lower extremity
    'EA': 'Ухо',                // Ear
    'TR': 'Туловище',           // Trunk (общий код для туловища)
    'FT': 'Стопа',              // Foot
    'AC': 'Акральная область',  // Acral
    'AB': 'Живот',              // Abdomen
    'BK': 'Спина',              // Back
    'CH': 'Грудь',              // Chest
    'FA': 'Лицо',               // Face
    'HA': 'Кисть'               // Hand
};

// --- Опции для выпадающего списка (для отправки кодов) ---

export const diseaseOptions = [
    { value: 'NV', text: 'Меланоцитарные невусы' },
    { value: 'MEL', text: 'Меланома' },
    { value: 'BCC', text: 'Базально-клеточная карцинома' },
    { value: 'BKL', text: 'Доброкачественные кератозоподобные поражения' },
    { value: 'AK', text: 'Актинический кератоз' },
    { value: 'DF', text: 'Дерматофиброма' },
    { value: 'VASC', text: 'Сосудистые поражения' },
];

export const locationOptions = [
    { value: 'TR', text: 'Туловище' },
    { value: 'LE', text: 'Нижняя конечность' },
    { value: 'UE', text: 'Верхняя конечность' },
    { value: 'SC', text: 'Волосистая часть головы' },
    { value: 'NK', text: 'Шея' },
    { value: 'FA', text: 'Лицо' },
    { value: 'AB', text: 'Живот' },
    { value: 'BK', text: 'Спина' },
    { value: 'CH', text: 'Грудь' },
    { value: 'GE', text: 'Гениталии' },
    { value: 'EA', text: 'Ухо' },
    { value: 'FT', text: 'Стопа' },
    { value: 'HA', text: 'Кисть' },
    { value: 'AC', text: 'Акральная область' },
    { value: 'UK', text: 'Неизвестно' },
];