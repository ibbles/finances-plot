class Tab:
    def init(self, notebook, transactions, by_account, resample_rule):
        """
        Tab initialization function. Subclasses of Tab should override this
        function to populate itself with widgets.
        """
        print("Tab.init")
