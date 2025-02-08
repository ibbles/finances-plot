class Tab:
    def init(
        self, notebook, transactions, by_account, by_category, resample_rule, verbose
    ):
        """
        Tab initialization function. Subclasses of Tab should override this
        function to populate itself with widgets.
        """
        print("Tab.init")
