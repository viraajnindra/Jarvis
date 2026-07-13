use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Emitter, Manager,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

fn show_main(app: &tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let summon = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyJ);
    // Emergency stop: global, works even when the window is hidden in the tray.
    let estop = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyX);

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    if shortcut == &summon {
                        show_main(app);
                    } else if shortcut == &estop {
                        show_main(app);
                        let _ = app.emit("emergency-stop", ());
                    }
                })
                .build(),
        )
        .setup(move |app| {
            app.global_shortcut().register(summon)?;
            app.global_shortcut().register(estop)?;

            let show = MenuItem::with_id(app, "show", "Show J.A.R.V.I.S.", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(true)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
