"""Main bot entry point for the Telegram Digital Products Store."""

import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config import settings, validate_settings
from database import init_db
from database.init_data import initialize_database
from handlers import user_handlers, admin_handlers, payment_handlers, admin_conversations, dispute_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and start the bot."""
    # Validate configuration
    try:
        validate_settings()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Initialize database
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return

    # Create application
    application = Application.builder().token(settings.BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", user_handlers.start_command))
    application.add_handler(CommandHandler("admin", admin_handlers.admin_command))

    # ==================== টপ-আপ কনভার্সেশন (আপডেটেড) ====================
    topup_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_handlers.topup_start, pattern="^topup$")],
        states={
            payment_handlers.AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, payment_handlers.topup_amount)
            ],
            payment_handlers.METHOD: [
                CallbackQueryHandler(payment_handlers.payment_method_selected, pattern="^method_"),
                CallbackQueryHandler(payment_handlers.cancel_topup, pattern="^cancel$")
            ],
            payment_handlers.TXID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, payment_handlers.topup_txid)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(payment_handlers.cancel_topup, pattern="^cancel$"),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(topup_conv_handler)

    # ==================== ডাইরেক্ট পারচেজ কনভার্সেশন ====================
    purchase_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_handlers.buy_product_start, pattern="^buy_")],
        states={
            payment_handlers.PURCHASE_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, payment_handlers.purchase_quantity_input),
                CallbackQueryHandler(payment_handlers.cancel_purchase, pattern="^cancel_purchase$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(payment_handlers.cancel_purchase, pattern="^cancel_purchase$"),
            MessageHandler(filters.COMMAND, payment_handlers.cancel_purchase)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(purchase_conv)

    # ==================== প্রোডাক্ট ক্রিয়েশন কনভার্সেশন ====================
    create_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.create_product_start, pattern="^admin_create_product$")],
        states={
            admin_conversations.PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.product_name),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.product_desc),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.product_price),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_TYPE: [
                CallbackQueryHandler(admin_conversations.product_type, pattern="^type_"),
                CallbackQueryHandler(admin_conversations.product_type, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_CATEGORY: [
                CallbackQueryHandler(admin_conversations.product_category, pattern="^cat_"),
                CallbackQueryHandler(admin_conversations.product_category, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_SUBCATEGORY: [
                CallbackQueryHandler(admin_conversations.product_subcategory, pattern="^subcat_"),
                CallbackQueryHandler(admin_conversations.product_subcategory, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_IMAGE: [
                MessageHandler(filters.PHOTO | filters.TEXT, admin_conversations.product_image),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_DOWNLOAD_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.product_download_link),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
            admin_conversations.PRODUCT_KEYS: [
                MessageHandler(filters.Document.ALL, admin_conversations.product_keys),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.product_keys),
                CallbackQueryHandler(admin_conversations.cancel_product_creation, pattern="^cancel_product$")
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_product_creation),
            CallbackQueryHandler(admin_conversations.cancel_product_creation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(create_product_conv)

    # ==================== প্রোডাক্ট এডিট কনভার্সেশন ====================
    edit_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.edit_product_start, pattern="^admin_edit_product$")],
        states={
            admin_conversations.EDIT_SELECT_PRODUCT: [
                CallbackQueryHandler(admin_conversations.edit_select_product, pattern="^edit_prod_"),
                CallbackQueryHandler(admin_conversations.edit_select_product, pattern="^admin_edit_product_page_"),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^admin_products$")
            ],
            admin_conversations.EDIT_SELECT_FIELD: [
                CallbackQueryHandler(admin_conversations.edit_select_field, pattern="^edit_"),
                CallbackQueryHandler(admin_conversations.edit_select_field, pattern="^cancel_edit$")
            ],
            admin_conversations.EDIT_NEW_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.edit_new_value),
                CallbackQueryHandler(admin_conversations.edit_new_value, pattern="^newprodcat_"),
                CallbackQueryHandler(admin_conversations.edit_new_value, pattern="^newprodsubcat_"),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^cancel_edit$")
            ],
            admin_conversations.EDIT_IMAGE_VALUE: [
                MessageHandler(filters.PHOTO, admin_conversations.edit_image_value),
                CallbackQueryHandler(admin_conversations.edit_image_value, pattern="^remove_product_image$"),
                CallbackQueryHandler(admin_conversations.edit_image_value, pattern="^cancel_edit$")
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(edit_product_conv)

    # ==================== ক্যাটাগরি ক্রিয়েশন কনভার্সেশন ====================
    create_category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.create_category_start, pattern="^admin_create_category$")],
        states={
            admin_conversations.CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.category_name)],
            admin_conversations.CATEGORY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.category_desc)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(create_category_conv)

    # ==================== সাবক্যাটাগরি ক্রিয়েশন কনভার্সেশন ====================
    create_subcategory_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.create_subcategory_start, pattern="^admin_create_subcategory$")],
        states={
            admin_conversations.SUBCATEGORY_CATEGORY: [
                CallbackQueryHandler(admin_conversations.subcategory_category, pattern="^subcat_cat_"),
                CallbackQueryHandler(admin_conversations.subcategory_category, pattern="^cancel_subcat$")
            ],
            admin_conversations.SUBCATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.subcategory_name)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(create_subcategory_conv)

    # ==================== ক্যাটাগরি এডিট কনভার্সেশন ====================
    edit_category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.edit_category_start, pattern="^admin_edit_category$")],
        states={
            admin_conversations.EDIT_CATEGORY_SELECT: [
                CallbackQueryHandler(admin_conversations.edit_category_select, pattern="^edit_cat_"),
                CallbackQueryHandler(admin_conversations.edit_category_select, pattern="^admin_edit_category_page_"),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^admin_manage_categories$")
            ],
            admin_conversations.EDIT_CATEGORY_FIELD: [
                CallbackQueryHandler(admin_conversations.edit_category_field, pattern="^editcat_"),
                CallbackQueryHandler(admin_conversations.edit_category_field, pattern="^cancel_edit_cat$")
            ],
            admin_conversations.EDIT_CATEGORY_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.edit_category_value),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^cancel_edit_cat$")
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(edit_category_conv)

    # ==================== সাবক্যাটাগরি এডিট কনভার্সেশন ====================
    edit_subcategory_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.edit_subcategory_start, pattern="^admin_edit_subcategory$")],
        states={
            admin_conversations.EDIT_SUBCATEGORY_SELECT: [
                CallbackQueryHandler(admin_conversations.edit_subcategory_select, pattern="^edit_subcat_"),
                CallbackQueryHandler(admin_conversations.edit_subcategory_select, pattern="^admin_edit_subcategory_page_"),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^admin_manage_categories$")
            ],
            admin_conversations.EDIT_SUBCATEGORY_FIELD: [
                CallbackQueryHandler(admin_conversations.edit_subcategory_field, pattern="^editsubcat_"),
                CallbackQueryHandler(admin_conversations.edit_subcategory_field, pattern="^cancel_edit_subcat$")
            ],
            admin_conversations.EDIT_SUBCATEGORY_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.edit_subcategory_value),
                CallbackQueryHandler(admin_conversations.edit_subcategory_value, pattern="^newcat_"),
                CallbackQueryHandler(admin_conversations.cancel_conversation, pattern="^cancel_edit_subcat$")
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(edit_subcategory_conv)

    # ==================== সাপোর্ট ইউজারনেম কনফিগারেশন ====================
    config_support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.config_support_username, pattern="^admin_support_username$")],
        states={
            admin_conversations.SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.setting_value)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(config_support_conv)

    # ==================== চ্যানেল ইউজারনেম কনফিগারেশন ====================
    config_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.config_channel_username, pattern="^admin_channel_username$")],
        states={
            admin_conversations.SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.setting_value)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_conversation),
            CallbackQueryHandler(admin_conversations.cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(config_channel_conv)

    # ==================== ওয়েলকাম মেসেজ কনফিগারেশন ====================
    config_welcome_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.config_welcome_message, pattern="^admin_welcome_msg$")],
        states={
            admin_conversations.WELCOME_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.welcome_message_value)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_settings),
            CallbackQueryHandler(admin_conversations.cancel_settings, pattern="^cancel$")
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(config_welcome_conv)

    # ==================== স্টোর লোগো কনফিগারেশন ====================
    config_logo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.config_store_logo, pattern="^admin_store_logo$")],
        states={
            admin_conversations.STORE_LOGO: [MessageHandler(filters.PHOTO, admin_conversations.store_logo_value)],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, admin_conversations.cancel_settings),
            CallbackQueryHandler(admin_conversations.cancel_settings, pattern="^cancel$")
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(config_logo_conv)

    # ==================== টেক্সট ব্রডকাস্ট কনভার্সেশন ====================
    broadcast_text_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.broadcast_text_start, pattern="^admin_broadcast_text$")],
        states={
            admin_conversations.BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.broadcast_text_message)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_conversations.cancel_broadcast, pattern="^cancel$"),
            MessageHandler(filters.COMMAND, admin_conversations.cancel_broadcast)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(broadcast_text_conv)

    # ==================== ইমেজ + টেক্সট ব্রডকাস্ট কনভার্সেশন ====================
    broadcast_image_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_conversations.broadcast_image_start, pattern="^admin_broadcast_image$")],
        states={
            admin_conversations.BROADCAST_IMAGE: [
                MessageHandler(filters.PHOTO, admin_conversations.broadcast_image_photo)
            ],
            admin_conversations.BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_conversations.broadcast_image_text)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_conversations.cancel_broadcast, pattern="^cancel$"),
            MessageHandler(filters.COMMAND, admin_conversations.cancel_broadcast)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(broadcast_image_conv)

    # ==================== ডিসপিউট কনভার্সেশন ====================
    dispute_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(dispute_handlers.open_dispute_start, pattern="^open_dispute_")],
        states={
            dispute_handlers.DISPUTE_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, dispute_handlers.dispute_reason_received)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(dispute_handlers.dispute_cancel, pattern="^cancel$"),
            MessageHandler(filters.COMMAND, dispute_handlers.dispute_cancel)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
    application.add_handler(dispute_conv)

    # ==================== রিস্টক কিস কনভার্সেশন ====================
    restock_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_handlers.admin_select_product_restock_callback, pattern="^select_product_")],
        states={
            admin_handlers.WAITING_FOR_KEYS: [
                MessageHandler(filters.Document.ALL & filters.User(settings.ADMIN_TELEGRAM_ID), admin_handlers.handle_restock_keys_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(settings.ADMIN_TELEGRAM_ID), admin_handlers.handle_restock_keys_paste),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_handlers.cancel_restock, pattern="^cancel_restock$"),
            CommandHandler("cancel", admin_handlers.cancel_restock, filters=filters.User(settings.ADMIN_TELEGRAM_ID)),
        ],
    )
    application.add_handler(restock_conv)

    # ==================== ইউজার কলব্যাক হ্যান্ডলার ====================
    application.add_handler(CallbackQueryHandler(user_handlers.main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(user_handlers.main_menu_callback, pattern="^back$"))
    application.add_handler(CallbackQueryHandler(user_handlers.back_to_products_callback, pattern="^back_to_products$"))
    application.add_handler(CallbackQueryHandler(user_handlers.products_callback, pattern="^products"))
    application.add_handler(CallbackQueryHandler(user_handlers.category_callback, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(user_handlers.subcategory_callback, pattern="^subcategory_"))
    application.add_handler(CallbackQueryHandler(user_handlers.product_callback, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(user_handlers.availability_callback, pattern="^availability$"))
    application.add_handler(CallbackQueryHandler(user_handlers.support_callback, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(user_handlers.order_history_callback, pattern="^order_history"))
    application.add_handler(CallbackQueryHandler(user_handlers.user_order_detail_callback, pattern="^user_order_detail_"))

    # ==================== পারচেজ কনফর্মেশন ও ক্যানসেল হ্যান্ডলার ====================
    application.add_handler(CallbackQueryHandler(payment_handlers.confirm_purchase, pattern="^confirm_purchase_"))
    application.add_handler(CallbackQueryHandler(payment_handlers.cancel_purchase, pattern="^cancel_purchase$"))

    # ==================== অ্যাডমিন কলব্যাক হ্যান্ডলার ====================
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_menu_callback, pattern="^admin_menu$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_products_callback, pattern="^admin_products"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_restock_keys_callback, pattern="^admin_restock_keys$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_manage_categories_callback, pattern="^admin_manage_categories$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_view_categories_callback, pattern="^admin_view_categories$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_view_users_callback, pattern="^admin_view_users"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_user_detail_callback, pattern="^view_user_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_ban_user_callback, pattern="^ban_user_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_unban_user_callback, pattern="^unban_user_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_view_orders_callback, pattern="^admin_view_orders"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_confirm_order_menu, pattern="^admin_confirm_order$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_cancel_order_menu, pattern="^admin_cancel_order$"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_confirm_payment_callback, pattern="^confirm_payment_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_cancel_payment_callback, pattern="^cancel_payment_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_order_detail_callback, pattern="^view_order_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_complete_order_callback, pattern="^complete_order_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_cancel_order_callback, pattern="^cancel_order_"))
    application.add_handler(CallbackQueryHandler(dispute_handlers.admin_view_disputes_callback, pattern="^admin_view_disputes"))
    application.add_handler(CallbackQueryHandler(dispute_handlers.admin_dispute_detail_callback, pattern="^admin_dispute_detail_"))
    application.add_handler(CallbackQueryHandler(dispute_handlers.admin_resolve_dispute_callback, pattern="^resolve_dispute_"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_users_callback, pattern="^admin_users"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_orders_callback, pattern="^admin_orders"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_settings_callback, pattern="^admin_settings"))
    application.add_handler(CallbackQueryHandler(admin_handlers.admin_broadcast_callback, pattern="^admin_broadcast"))

    # ==================== নতুন: অ্যাডমিন পেমেন্ট রিকোয়েস্ট হ্যান্ডলার ====================
    application.add_handler(CallbackQueryHandler(payment_handlers.admin_payment_requests, pattern="^admin_payments$"))
    application.add_handler(CallbackQueryHandler(payment_handlers.admin_confirm_payment, pattern="^confirm_payment_"))

    # ==================== গ্লোবাল ক্যানসেল হ্যান্ডলার ====================
    application.add_handler(CallbackQueryHandler(payment_handlers.cancel_payment_page, pattern="^cancel$"))

    # ==================== শিডিউল জব ====================
    job_queue = application.job_queue

    # পেমেন্ট চেকিং
    job_queue.run_repeating(
        payment_handlers.check_pending_payments,
        interval=settings.PAYMENT_CHECK_INTERVAL,
        first=10
    )
    job_queue.run_repeating(
        payment_handlers.check_expired_payments,
        interval=60,
        first=30
    )

    # অ্যাভেইলেবিলিটি ব্রডকাস্ট (১২ ঘন্টা পরপর)
    logger.info("Scheduling availability broadcast job (first run in 10 seconds, then every 12 hours)")
    job_queue.run_repeating(
        payment_handlers.broadcast_availability_to_all_users,
        interval=43200,
        first=10
    )

    # স্টার্ট বট
    logger.info("Bot started successfully!")
    logger.info("Availability broadcast will run in 10 seconds...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()